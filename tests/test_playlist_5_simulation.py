import tempfile
import unittest
from pathlib import Path
from core.download_manager import DownloadManager
from core.storage import JsonStore
from test_cumulative_progress import FakeEngine, wait_until


class TestFiveDownloads(unittest.TestCase):
    def test_real_worker_processes_five_jobs_with_one_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = DownloadManager(lambda *_: None, JsonStore(Path(tmp)/"queue.json"), FakeEngine)
            try:
                for video in ["one", "two", "bad", "four", "five"]:
                    manager.submit(f"https://youtube.com/watch?v={video}", "MP3", "192 kbps", tmp, start=False)
                manager.resume()
                wait_until(lambda: manager.snapshot()[-1]["status"] == "completed", 8)
                states = [job["status"] for job in manager.snapshot()]
                self.assertEqual(states, ["completed", "completed", "failed", "completed", "completed"])
            finally:
                manager.close()
                manager._worker.join(3)
                manager._resolver.join(3)
