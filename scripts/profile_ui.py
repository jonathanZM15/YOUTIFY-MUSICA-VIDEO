r"""Measure startup, idle CPU/RAM, event-loop delay and UI actions without downloads.

Uses an isolated temporary profile; prints results without creating build artifacts.
Run: .venv\Scripts\python scripts/profile_ui.py --seconds 8 --jobs 0 --profile
"""
import argparse
import cProfile
import json
import os
from pathlib import Path
import pstats
import statistics
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', type=float, default=8)
    parser.add_argument('--jobs', type=int, default=0)
    parser.add_argument('--profile', action='store_true')
    args = parser.parse_args()
    if not 0 <= args.jobs <= 2000 or not 1 <= args.seconds <= 60:
        parser.error('Use 0..2000 jobs and 1..60 seconds')
    with tempfile.TemporaryDirectory(prefix='youtify-perf-') as directory:
        os.environ['YOUTIFY_DATA_DIR'] = directory
        jobs = [dict(id=str(i), url=f'https://youtube.com/watch?v=bench{i}', title=f'Pista de prueba {i}',
            format_type='MP3 (audio)', quality='192 kbps', destination=directory,
            status='pending') for i in range(args.jobs)]
        Path(directory, 'queue.json').write_text(json.dumps(jobs), encoding='utf-8')
        import psutil
        process = psutil.Process()
        started = time.perf_counter()
        from ui.app_window import AppWindow
        app = AppWindow()
        app.geometry('1000x640')
        report = {'jobs': args.jobs, 'startup_seconds': time.perf_counter()-started}
        profiler = cProfile.Profile()
        gaps, action_times = [], {}
        last_tick = time.perf_counter()
        measuring = False

        def heartbeat():
            nonlocal last_tick
            now = time.perf_counter()
            if measuring: gaps.append(now-last_tick)
            last_tick = now
            if not app._closing: app.after(50, heartbeat)

        def begin():
            nonlocal measuring
            measuring = True
            report['_start'] = time.perf_counter()
            report['_cpu'] = sum(process.cpu_times()[:2])
            report['_threads'] = {t.id:t.user_time+t.system_time for t in process.threads()}
            if args.profile: profiler.enable()
            app.after(round(args.seconds*1000), finish_idle)

        def finish_idle():
            nonlocal measuring
            if args.profile: profiler.disable()
            measuring = False
            elapsed = time.perf_counter()-report.pop('_start')
            cpu = (sum(process.cpu_times()[:2])-report.pop('_cpu'))/elapsed*100
            thread_start = report.pop('_threads')
            names = {t.native_id:t.name for t in threading.enumerate()}
            report['thread_cpu_ms'] = {names.get(t.id,str(t.id)):round((t.user_time+t.system_time-thread_start.get(t.id,0))*1000,2)
                for t in process.threads()}
            report.update(idle_cpu_one_core_pct=cpu, idle_cpu_machine_pct=cpu/(psutil.cpu_count() or 1),
                rss_mb=process.memory_info().rss/1024**2, private_mb=process.memory_info().private/1024**2,
                idle_tick_max_ms=max(gaps, default=0)*1000,
                idle_tick_p95_ms=sorted(gaps)[min(len(gaps)-1,int(len(gaps)*.95))]*1000 if gaps else 0,
                yt_dlp_loaded='yt_dlp' in sys.modules)
            run_action(0)

        def popup(select):
            select.open()
            app.update_idletasks()
            select.close()

        def format_change(value):
            app.download_card.format_menu.set(value)
            app.download_card._handle_format_change(value)

        actions = [
            ('format_popup', lambda:popup(app.download_card.format_menu)),
            ('quality_popup', lambda:popup(app.download_card.quality_menu)),
            ('theme_popup', lambda:popup(app.header.theme_menu)),
            ('theme_light', lambda:app._change_theme('Claro')),
            ('theme_dark', lambda:app._change_theme('Oscuro')),
            ('format_mp4', lambda:format_change('MP4 (video)')),
            ('format_mp3', lambda:format_change('MP3 (audio)')),
            ('reset_folder', app._reset_destination),
            ('pause', app.manager.pause),
            ('clear_finished', app.manager.clear_finished),
            ('activity_tab', lambda:app.tabs.set('Actividad')),
            ('queue_tab', lambda:app.tabs.set('Cola')),
        ]

        def run_action(index):
            if index >= len(actions)*3:
                report['actions_ms'] = {name: {'median':round(statistics.median(values),2),
                    'max':round(max(values),2)} for name, values in action_times.items()}
                print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
                if args.profile: pstats.Stats(profiler, stream=sys.stdout).sort_stats('cumulative').print_stats(30)
                app._on_window_closing()
                return
            name, command = actions[index % len(actions)]
            start = time.perf_counter()
            command()
            app.update_idletasks()
            action_times.setdefault(name, []).append((time.perf_counter()-start)*1000)
            app.after(70, lambda:run_action(index+1))

        app.after(50, heartbeat)
        app.after(1200, begin)
        app.mainloop()


if __name__ == '__main__':
    main()
