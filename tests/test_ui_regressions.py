from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from ui.app_window import AppWindow
from ui.components.preview_card import PreviewCard
from ui.components.progress_bar import ProgressBarWidget
from core.storage import JsonStore
from core.download_manager import DownloadManager
from core.updater import ReleaseInfo, Updater


class TestPreviewRaces(unittest.TestCase):
    def test_old_metadata_does_not_clear_current_preview(self):
        app = SimpleNamespace(_preview_busy=True, _preview_url="https://youtube.com/watch?v=new",
            preview_card=MagicMock(), _inspect_url_async=MagicMock())
        AppWindow._apply_preview(app, "https://youtube.com/watch?v=old", None)
        app.preview_card.hide_preview.assert_not_called()
        app._inspect_url_async.assert_called_once_with(app._preview_url)

    def test_thumbnail_only_uses_youtube_image_hosts(self):
        self.assertTrue(PreviewCard._valid_thumbnail("https://i.ytimg.com/vi/id/hqdefault.jpg"))
        for url in ["https://127.0.0.1/x", "http://i.ytimg.com/x", "https://i.ytimg.com.evil.example/x"]:
            self.assertFalse(PreviewCard._valid_thumbnail(url))


class TestActualWidgets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.patches = [patch("ui.app_window.PREFERENCES_FILE", Path(cls.tmp.name)/"prefs.json"),
            patch("core.download_manager.QUEUE_FILE", Path(cls.tmp.name)/"queue.json"),
            patch("ui.app_window.Updater.check_and_update_async"), patch("ui.app_window.Updater.check_app_update_async")]
        for item in cls.patches: item.start()
        try:
            cls.app = AppWindow()
            cls.app.withdraw()
            cls.app.update_idletasks()
        except Exception:
            for item in cls.patches: item.stop()
            cls.tmp.cleanup()
            raise

    @classmethod
    def tearDownClass(cls):
        cls.app._closing = True
        cls.app.manager.close()
        cls.app.manager._worker.join(3)
        cls.app.manager._resolver.join(3)
        cls.app.destroy()
        for item in cls.patches: item.stop()
        cls.tmp.cleanup()

    def test_format_switch_replaces_quality_options(self):
        self.app.download_card._handle_format_change("MP4 (video)")
        self.assertIn("1080p", self.app.download_card.quality_menu.cget("values"))
        self.app.download_card._handle_format_change("MP3 (audio)")
        self.assertIn("192 kbps", self.app.download_card.quality_menu.cget("values"))

    def test_conversion_has_distinct_text_and_never_100_percent(self):
        self.app.progress_widget.set_converting()
        self.assertIn("Convirtiendo", self.app.progress_widget.status_badge.cget("text"))
        self.assertLess(self.app.progress_widget.progress_bar.get(), 1)

    def test_failed_queue_does_not_show_success(self):
        job = dict(id="test", url="https://youtube.com/watch?v=x", format_type="MP3", quality="192 kbps", destination=self.tmp.name,
            title="Failed fixture", status="failed", error="No disponible", filepath="")
        self.app._render_queue({"jobs": [job], "paused": True})
        self.assertIn("error", self.app.progress_widget.status_badge.cget("text"))
        self.assertIn("con error", self.app.queue_summary.cget("text"))

    def test_custom_folder_is_persisted_and_resettable(self):
        self.app._custom_destination = Path(self.tmp.name)
        self.app._save_preferences()
        self.assertEqual(self.app._preferences.read()["destination"], self.tmp.name)
        self.app._reset_destination()
        self.assertIsNone(self.app._custom_destination)

    def test_worker_events_do_not_touch_widgets_before_dispatch(self):
        with patch.object(self.app.console_view, "append_logs") as append:
            self.app._emit("log", "Worker message")
            append.assert_not_called()
            self.app._drain_events()
            self.assertTrue(any("Worker message" in str(call) for call in append.call_args_list))

    def test_identical_queue_snapshot_does_not_redraw_rows(self):
        view = self.app.queue_view
        jobs = [dict(id='stable',format_type='MP3',quality='192 kbps',destination=self.tmp.name,
            title='Stable',status='pending',error='',filepath='')]
        try:
            view.render(jobs)
            row = view.rows['stable']
            with patch.object(row['button'],'configure') as configure:
                view.render([dict(jobs[0])])
                configure.assert_not_called()
                view.render([{**jobs[0],'status':'completed','filepath':'saved.mp3'}])
                self.assertEqual(configure.call_args.kwargs['text'],'Abrir')
        finally: view.render([])

    def test_batched_logs_are_sanitized_bounded_and_keep_newest_lines(self):
        from config.settings import MAX_LOG_BUFFER_LINES
        console = self.app.console_view
        console.clear_logs()
        console.append_logs([f'\x1b[31mLine {i}\x1b[0m' for i in range(MAX_LOG_BUFFER_LINES+80)])
        text = console.textbox.get('1.0','end-1c')
        self.assertNotIn('\x1b',text)
        self.assertEqual(len(text.splitlines()),MAX_LOG_BUFFER_LINES)
        self.assertTrue(text.startswith('Line 80\n'))
        self.assertEqual(console.textbox.cget('state'),'disabled')
        console.clear_logs()

    def test_unchanged_progress_does_not_redraw_or_relayout(self):
        widget = self.app.progress_widget
        progress = dict(total=5,completed=1,failed=0,cancelled=0,done=1,value=.3,reading=False)
        try:
            widget.set_playlist_progress(progress)
            widget.set_progress(.3)
            with patch.object(widget.playlist_panel,'grid') as grid, \
                    patch.object(widget.playlist_bar,'set') as total, \
                    patch.object(widget.progress_bar,'set') as file:
                widget.set_playlist_progress(dict(progress))
                widget.set_progress(.3)
                grid.assert_not_called()
                total.assert_not_called()
                file.assert_not_called()
        finally: widget.set_playlist_progress(None)

    def test_large_playlist_creates_only_one_page_of_widgets(self):
        jobs = [dict(id=str(i), url=f"https://youtube.com/watch?v={i}", format_type="MP3", quality="192 kbps",
            destination=self.tmp.name, title=f"Video {i}", status="pending", error="", filepath="") for i in range(2000)]
        self.app.queue_view.render(jobs)
        self.assertEqual(len(self.app.queue_view.rows), 25)
        self.app.queue_view._turn_page(1)
        self.assertEqual(len(self.app.queue_view.rows), 25)
        self.assertIn("25", self.app.queue_view.rows)
        self.app.queue_view.render([])

    def test_background_queue_updates_are_coalesced(self):
        for i in range(1000):
            self.app._emit("queue", {"jobs": [], "paused": True, "test_sequence": i})
        self.assertEqual(self.app._pending_queue["test_sequence"], 999)
        self.assertLessEqual(self.app._events.qsize(), 500)

    def test_bad_background_callback_does_not_stop_following_events(self):
        delivered = []
        self.app._emit("call", lambda: (_ for _ in ()).throw(RuntimeError("fixture")))
        self.app._emit("call", lambda: delivered.append(True))
        with self.assertLogs("ui.app_window", level="ERROR"):
            self.app._drain_events()
        self.assertEqual(delivered, [True])

    def test_short_window_shows_quality_controls_and_download_queue(self):
        original = self.app.geometry()
        try:
            self.app.geometry("1000x640")
            self.app.deiconify()
            self.app.update()
            self.app.body._parent_canvas.yview_moveto(0)
            self.app.update_idletasks()
            quality = self.app.download_card.quality_menu
            canvas = self.app.body._parent_canvas
            self.assertLessEqual(quality.winfo_rooty() + quality.winfo_height(),
                canvas.winfo_rooty() + canvas.winfo_height())
            self.assertTrue(self.app.queue_view.winfo_ismapped())
            self.assertTrue(self.app.progress_widget.winfo_ismapped())
            self.assertLess(self.app.left_panel.winfo_rootx(), self.app.workspace.winfo_rootx())
        finally:
            self.app.geometry(original)
            self.app.withdraw()

    def test_update_notice_is_nonmodal_and_only_shown_once(self):
        release = ReleaseInfo('v9.0.0', '9.0.0', 'New', '', '', '')
        state = Path(self.tmp.name)/'updates.json'
        with patch('core.updater.UPDATE_STATE_FILE', state):
            self.app._show_update_ready(release)
            banner = self.app._update_banner
            self.assertIsNone(self.app.grab_current())
            self.assertEqual(Updater._read_update_state()['last_notified_tag'], 'v9.0.0')
            self.app._show_update_ready(release)
            self.assertIs(self.app._update_banner, banner)
            banner.destroy()
            self.app._update_banner = None

    def test_playlist_bar_only_appears_for_playlist_context(self):
        widget = self.app.progress_widget
        progress = dict(total=10, completed=3, failed=0, cancelled=0, done=3, value=.347, reading=False)
        try:
            widget.set_playlist_progress(progress)
            self.assertEqual(widget.playlist_panel.winfo_manager(), 'grid')
            self.assertIn('3 de 10 guardadas',widget.playlist_label.cget('text'))
            self.assertEqual(widget.playlist_percent.cget('text'),'34 %')
            widget.set_progress(.47)
            self.assertIn('47 % del archivo',widget.percent.cget('text'))
            self.assertAlmostEqual(widget.playlist_bar.get(),.347)
            widget.set_playlist_progress(None)
            self.assertEqual(widget.playlist_panel.winfo_manager(),'')
        finally: widget.set_playlist_progress(None)

    def test_playlist_never_rounds_to_100_before_last_file_is_saved(self):
        widget = self.app.progress_widget
        try:
            widget.set_playlist_progress(dict(total=10, completed=9, failed=0, cancelled=0, done=9, value=.997, reading=False))
            self.assertEqual(widget.playlist_percent.cget('text'),'99 %')
            widget.set_playlist_progress(dict(total=10, completed=9, failed=1, cancelled=0, done=10, value=1, reading=False))
            self.assertEqual(widget.playlist_percent.cget('text'),'100 %')
            self.assertIn('1 con error',widget.playlist_label.cget('text'))
            self.assertIn('9 guardadas',widget.playlist_label.cget('text'))
        finally: widget.set_playlist_progress(None)

    def test_short_window_keeps_controls_visible_with_two_progress_bars(self):
        original = self.app.geometry()
        try:
            self.app.geometry('1000x620')
            self.app.progress_widget.set_playlist_progress(dict(total=8, completed=3, failed=0, cancelled=0, done=3, value=.4, reading=False))
            self.app.deiconify()
            self.app.update()
            self.app.body._parent_canvas.yview_moveto(0)
            self.app.update_idletasks()
            widget = self.app.progress_widget
            self.assertTrue(widget.playlist_bar.winfo_ismapped())
            self.assertLess(widget.playlist_bar.winfo_rooty()+widget.playlist_bar.winfo_height(), self.app.winfo_rooty()+self.app.winfo_height())
            quality, canvas = self.app.download_card.quality_menu, self.app.body._parent_canvas
            self.assertLessEqual(quality.winfo_rooty()+quality.winfo_height(), canvas.winfo_rooty()+canvas.winfo_height())
            cover = self.app.download_card.thumbnail_checkbox
            self.assertLessEqual(cover.winfo_rooty()+cover.winfo_height(), canvas.winfo_rooty()+canvas.winfo_height())
        finally:
            self.app.progress_widget.set_playlist_progress(None)
            self.app.geometry(original)
            self.app.withdraw()

    def test_stale_progress_cannot_reset_a_newer_playlist_total(self):
        app = self.app
        old_revision = app._render_revision
        try:
            job = dict(id='active',url='https://youtube.com/watch?v=x',format_type='MP3',quality='192 kbps',
                destination=self.tmp.name,title='Active',status='downloading',filepath='',error='')
            current = dict(total=10,completed=5,failed=0,cancelled=0,done=5,value=.55,reading=False)
            app._pending_queue = None
            app._render_queue(dict(jobs=[job],paused=False,playlist=current,revision=100,current_progress=.5))
            app._emit('progress',dict(id='active',value=.1,speed='',eta='',playlist={**current,'value':.1},revision=99))
            app._drain_events()
            self.assertAlmostEqual(app.progress_widget.playlist_bar.get(),.55)
            self.assertAlmostEqual(app.progress_widget.progress_bar.get(),.5)
        finally:
            app._render_revision=old_revision
            app.progress_widget.set_playlist_progress(None)
