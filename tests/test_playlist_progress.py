from pathlib import Path
import tempfile
import unittest

from core.download_manager import DownloadManager, DownloadJob
from core.storage import JsonStore
from test_cumulative_progress import wait_until


class TestPlaylistProgress(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.events = []
        self.store = JsonStore(Path(self.tmp.name)/'queue.json')
        self.manager = DownloadManager(lambda *event:self.events.append(event), self.store, autostart=False)

    def tearDown(self):
        self.manager.close()
        if self.manager._resolver.is_alive(): self.manager._resolver.join(2)
        self.tmp.cleanup()

    def playlist(self, count=10):
        self.manager.resolver = lambda url:[f'https://youtube.com/watch?v=track{i}' for i in range(count)]
        self.manager.submit('https://youtube.com/playlist?list=PLtest', 'MP3', '192 kbps', self.tmp.name, start=False)
        self.manager._resolver.start()
        wait_until(lambda:len(self.manager.snapshot())==count and all(j['status']=='pending' for j in self.manager.snapshot()))
        return self.manager.jobs

    def test_single_video_and_multiple_individual_links_have_no_playlist_bar(self):
        for video in ('a','b','c'):
            self.manager.submit(f'https://youtube.com/watch?v={video}', 'MP3', '192 kbps', self.tmp.name, start=False)
        self.assertIsNone(self.manager.queue_state()['playlist'])

    def test_reading_playlist_has_unknown_total_until_resolution(self):
        self.manager.submit('https://youtube.com/playlist?list=PLtest', 'MP3', '192 kbps', self.tmp.name, start=False)
        progress = self.manager.queue_state()['playlist']
        self.assertTrue(progress['reading'])
        self.assertEqual(progress['total'], 0)

    def test_total_includes_finished_tracks_and_current_fraction(self):
        jobs = self.playlist()
        for job in jobs[:3]: job.status='completed'
        jobs[3].status='downloading'
        self.manager._active_id = jobs[3].id
        self.manager._progress(jobs[3], .5, '50%', '1 MiB/s', '1')
        progress = self.events[-1][1]['playlist']
        self.assertEqual((progress['completed'], progress['total']), (3, 10))
        self.assertAlmostEqual(progress['value'], .347)
        self.manager._status(jobs[3], 'converting', 'Saving')
        self.assertAlmostEqual(self.manager.queue_state()['playlist']['value'], .397)
        jobs[3].status='completed'
        jobs[4].status='downloading'
        self.manager._active_id = jobs[4].id
        self.manager._progress_value=0
        self.assertAlmostEqual(self.manager.queue_state()['playlist']['value'], .4)

    def test_pause_preserves_total_and_never_completes_during_conversion(self):
        jobs = self.playlist(5)
        for job in jobs[:-1]: job.status='completed'
        jobs[-1].status='converting'
        self.manager._active_id=jobs[-1].id
        before = self.manager.queue_state()['playlist']['value']
        self.manager.pause()
        self.assertEqual(self.manager.queue_state()['playlist']['value'], before)
        self.assertLess(before, 1)

    def test_cancellation_failure_and_retry_have_separate_counts(self):
        jobs = self.playlist(5)
        jobs[0].status='completed'
        jobs[1].status='failed'
        self.manager.cancel(jobs[2].id)
        progress = self.manager.queue_state()['playlist']
        self.assertEqual((progress['completed'],progress['failed'],progress['cancelled']), (1,1,1))
        self.assertAlmostEqual(progress['value'], .6)
        self.manager.retry(jobs[2].id)
        self.assertEqual(self.manager.queue_state()['playlist']['cancelled'], 0)
        self.assertAlmostEqual(self.manager.queue_state()['playlist']['value'], .4)

    def test_old_downloads_and_other_playlists_are_not_added(self):
        jobs = self.playlist(5)
        old = DownloadJob('https://youtube.com/watch?v=old', 'MP3', '192 kbps', self.tmp.name, status='completed')
        other = DownloadJob('https://youtube.com/watch?v=other', 'MP3', '192 kbps', self.tmp.name, status='completed', playlist_id='other')
        self.manager.jobs[:0]=[old,other]
        jobs[2].status='completed'  # First member after prepended history.
        progress = self.manager.queue_state()['playlist']
        self.assertEqual((progress['completed'], progress['total']), (1,5))

    def test_active_single_hides_playlist_bar_and_next_playlist_restores_it(self):
        jobs = self.playlist(5)
        single = DownloadJob('https://youtube.com/watch?v=single', 'MP3', '192 kbps', self.tmp.name, status='downloading')
        self.manager.jobs.insert(0,single)
        self.manager._active_id=single.id
        self.assertIsNone(self.manager.queue_state()['playlist'])
        single.status='completed'
        self.manager._active_id=None
        self.assertEqual(self.manager.queue_state()['playlist']['total'],5)

    def test_trim_clear_and_restart_preserve_totals_above_history_limit(self):
        jobs = self.playlist(120)
        for job in jobs[:110]: job.status='completed'
        with self.manager._condition: self.manager._changed()
        progress = self.manager.queue_state()['playlist']
        self.assertEqual((progress['completed'],progress['total']), (110,120))
        self.manager.clear_finished()
        self.assertEqual(len(self.manager.snapshot()),10)
        restored = DownloadManager(lambda *_:None, self.store, autostart=False)
        try:
            progress = restored.queue_state()['playlist']
            self.assertEqual((progress['completed'],progress['total']), (110,120))
            for job in restored.jobs: job.status='completed'
            self.assertEqual(restored.queue_state()['playlist']['value'],1)
            restored.clear_finished()
            self.assertIsNone(restored.queue_state()['playlist'])
        finally: restored.close()

    def test_legacy_queue_list_is_migrated_without_losing_pending_jobs(self):
        self.store.write([dict(url='https://youtube.com/watch?v=old', format_type='MP3',quality='192 kbps',destination=self.tmp.name)])
        restored = DownloadManager(lambda *_:None, self.store, autostart=False)
        try:
            self.assertEqual(len(restored.snapshot()),1)
            self.assertIsNone(restored.queue_state()['playlist'])
            restored.close()
            self.assertEqual(self.store.read()['schema'],2)
        finally: restored.close()

    def test_late_progress_after_cancel_does_not_change_total(self):
        jobs = self.playlist(5)
        jobs[0].status='downloading'
        self.manager._active_id=jobs[0].id
        self.manager.cancel(jobs[0].id)
        count = len(self.events)
        self.manager._progress(jobs[0],1,'100%','','')
        self.assertEqual(len(self.events),count)

    def test_full_pending_capacity_survives_restart_alongside_history(self):
        jobs = [dict(url=f'https://youtube.com/watch?v=track{i}',format_type='MP3',quality='192 kbps',
            destination=self.tmp.name,status='completed' if i<100 else 'pending') for i in range(2100)]
        self.store.write(jobs)
        restored = DownloadManager(lambda *_:None,self.store,autostart=False)
        try:
            self.assertEqual(sum(j['status']=='pending' for j in restored.snapshot()),2000)
            self.assertEqual(len(restored.snapshot()),2100)
        finally: restored.close()
