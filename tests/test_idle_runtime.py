"""Regressions for startup imports, idle workers and unnecessary disk writes."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock
from core.download_manager import DownloadJob, DownloadManager


class TestIdleRuntime(unittest.TestCase):
    def test_opening_the_app_does_not_import_the_download_engine_library(self):
        with tempfile.TemporaryDirectory() as directory:
            code = '''
import sys
from ui.app_window import AppWindow
app = AppWindow()
app.withdraw()
app.update_idletasks()
assert "yt_dlp" not in sys.modules, "idle startup imported yt-dlp"
app._on_window_closing()
'''
            result = subprocess.run([sys.executable,'-c',code], cwd=Path(__file__).resolve().parent.parent,
                env={**os.environ,'YOUTIFY_DATA_DIR':directory}, capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stderr)

    def test_idle_workers_exit_when_closed_and_repeated_noops_do_not_write(self):
        store = Mock()
        store.read.return_value = []
        manager = DownloadManager(Mock(),store=store)
        try:
            manager.pause()
            manager.clear_finished()
            store.write.assert_not_called()
            manager.close()
            manager._resolver.join(2)
            manager._worker.join(2)
            self.assertFalse(manager._resolver.is_alive())
            self.assertFalse(manager._worker.is_alive())
            manager.close()
            store.write.assert_called_once()
        finally: manager.close()

    def test_snapshots_are_independent_of_live_jobs(self):
        store = Mock()
        store.read.return_value = []
        manager = DownloadManager(Mock(),store=store,autostart=False)
        manager.jobs = [DownloadJob('https://youtu.be/example','MP3','192 kbps','C:/music')]
        snapshot = manager.snapshot()
        snapshot[0]['status'] = 'completed'
        self.assertEqual(manager.jobs[0].status,'pending')
        manager.close()
