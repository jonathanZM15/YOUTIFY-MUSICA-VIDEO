import tempfile
import threading
import time
import unittest
from pathlib import Path
from core.download_manager import DownloadManager, DownloadJob
from core.downloader import DownloadCancelled
from core.storage import JsonStore


class FakeEngine:
    def __init__(self, on_progress, on_log, on_status):
        self.progress, self.status = on_progress, on_status
        self.cancelled = threading.Event()

    def execute_download(self, url, *args):
        if "bad" in url: raise RuntimeError("Not available")
        self.status("title", "Fixture video")
        self.progress(1, "100%", "1 MiB/s", "0")
        self.status("converting", "Saving")
        return {"title": "Fixture video", "filepath": "fixture.mp3"}

    def cancel(self): self.cancelled.set()


def wait_until(predicate, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate(): return
        time.sleep(0.01)
    raise AssertionError("Timed out waiting for queue")


class TestDownloadManager(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.events = []
        self.manager = DownloadManager(lambda kind, data: self.events.append((kind, data)),
            JsonStore(Path(self.tmp.name) / "queue.json"), FakeEngine)

    def tearDown(self):
        self.manager.close()
        self.manager._worker.join(3)
        self.manager._resolver.join(3)
        self.tmp.cleanup()

    def add(self, video="good", start=True):
        return self.manager.submit(f"https://youtube.com/watch?v={video}", "MP3", "192 kbps", self.tmp.name, start=start)

    def test_enqueue_waits_until_resumed(self):
        self.add(start=False)
        self.assertEqual(self.manager.snapshot()[0]["status"], "pending")
        self.manager.resume()
        wait_until(lambda: self.manager.snapshot()[0]["status"] == "completed")

    def test_failure_is_not_success_and_next_item_continues(self):
        self.add("bad", start=False)
        self.add("good", start=False)
        self.manager.resume()
        wait_until(lambda: self.manager.snapshot()[-1]["status"] == "completed")
        self.assertEqual([j["status"] for j in self.manager.snapshot()], ["failed", "completed"])

    def test_duplicates_are_not_enqueued_twice(self):
        first = self.add(start=False)
        second = self.add(start=False)
        self.assertEqual(first, second)
        self.assertEqual(len(self.manager.snapshot()), 1)

    def test_pending_can_be_cancelled_without_starting_it(self):
        job = self.add(start=False)
        self.manager.cancel(job)
        self.assertEqual(self.manager.snapshot()[0]["status"], "cancelled")

    def test_retry_cancelled_item(self):
        job = self.add(start=False)
        self.manager.cancel(job)
        self.manager.retry(job)
        wait_until(lambda: self.manager.snapshot()[0]["status"] == "completed")

    def test_download_progress_stays_below_100_until_postprocessing_finishes(self):
        self.add()
        wait_until(lambda: self.manager.snapshot()[0]["status"] == "completed")
        progress = [data["value"] for kind, data in self.events if kind == "progress"]
        self.assertTrue(progress)
        self.assertLess(max(progress), 1)

    def test_playlist_resolution_runs_off_calling_thread(self):
        started, release = threading.Event(), threading.Event()
        def resolver(url):
            started.set()
            release.wait(2)
            return ["https://youtube.com/watch?v=a", "https://youtube.com/watch?v=b"]
        self.manager.resolver = resolver
        now = time.monotonic()
        self.manager.submit("https://youtube.com/playlist?list=PLtest", "MP3", "192 kbps", self.tmp.name, start=False)
        self.assertLess(time.monotonic()-now, 0.3)
        self.assertTrue(started.wait(1))
        self.assertEqual(self.manager.snapshot()[0]["status"], "resolving")
        release.set()
        wait_until(lambda: len(self.manager.snapshot()) == 2)

    def test_cancelled_playlist_is_not_added_when_response_arrives(self):
        started, release = threading.Event(), threading.Event()
        def resolver(url):
            started.set(); release.wait(2)
            return ["https://youtube.com/watch?v=a"]
        self.manager.resolver = resolver
        job = self.manager.submit("https://youtube.com/playlist?list=PLtest", "MP3", "192 kbps", self.tmp.name, start=False)
        self.assertTrue(started.wait(1))
        self.manager.cancel(job)
        release.set()
        time.sleep(0.1)
        self.assertEqual(self.manager.snapshot()[0]["status"], "cancelled")

    def test_queue_survives_restart_and_waits_for_confirmation(self):
        self.add(start=False)
        restored = DownloadManager(lambda *_: None, self.manager.store, FakeEngine, autostart=False)
        self.assertEqual(restored.snapshot()[0]["status"], "pending")
        self.assertTrue(restored.paused)
        restored.close()

    def test_clear_finished_preserves_pending(self):
        job = self.add("cancel", start=False)
        self.manager.cancel(job)
        self.add("waiting", start=False)
        self.manager.clear_finished()
        self.assertEqual(len(self.manager.snapshot()), 1)
        self.assertEqual(self.manager.snapshot()[0]["status"], "pending")

    def test_playlist_failure_is_visible(self):
        self.manager.resolver = lambda url: []
        self.manager.submit("https://youtube.com/playlist?list=PLtest", "MP3", "192 kbps", self.tmp.name, start=False)
        wait_until(lambda: self.manager.snapshot()[0]["status"] == "failed")
        self.assertIn("playlist", self.manager.snapshot()[0]["error"])

    def test_active_cancel_never_becomes_completed(self):
        started = threading.Event()
        class SlowEngine(FakeEngine):
            def execute_download(self, url, *args):
                started.set()
                self.cancelled.wait(3)
                raise DownloadCancelled("cancelled")
        self.manager.engine_factory = SlowEngine
        job = self.add()
        self.assertTrue(started.wait(1))
        self.manager.cancel(job)
        wait_until(lambda: self.manager._active_id is None)
        self.assertEqual(self.manager.snapshot()[0]["status"], "cancelled")

    def test_close_restores_active_download_as_pending(self):
        started = threading.Event()
        class SlowEngine(FakeEngine):
            def execute_download(self, url, *args):
                started.set()
                self.cancelled.wait(3)
                raise DownloadCancelled("closing")
        self.manager.engine_factory = SlowEngine
        self.add()
        self.assertTrue(started.wait(1))
        self.manager.close()
        self.manager._worker.join(2)
        restored = DownloadManager(lambda *_: None, self.manager.store, FakeEngine, autostart=False)
        self.assertEqual(restored.snapshot()[0]["status"], "pending")
        restored.close()
