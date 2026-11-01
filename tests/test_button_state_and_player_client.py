"""Test options with real yt-dlp, rather than asserting dictionaries passed to a mock."""
from pathlib import Path
import unittest
from unittest.mock import patch
from yt_dlp import YoutubeDL
from core.downloader import DownloadEngine
from core.validator import SecurityValidator


class TestDownloadOptions(unittest.TestCase):
    def options(self, audio=False, quality="720p"):
        return DownloadEngine()._build_yt_dlp_options(audio, Path("C:/review"), Path("ffmpeg").resolve(), quality, False)

    def test_real_downloader_accepts_runtime_configuration(self):
        with YoutubeDL(self.options()) as ydl:
            self.assertFalse(ydl.params["remote_components"])

    def test_different_ids_produce_distinct_filenames(self):
        with YoutubeDL(self.options()) as ydl:
            first = ydl.prepare_filename({"title": "Same title", "id": "first", "ext": "mp4"})
            second = ydl.prepare_filename({"title": "Same title", "id": "second", "ext": "mp4"})
        self.assertNotEqual(first, second)

    def test_different_quality_produces_distinct_filenames(self):
        info = {"title": "Title", "id": "id", "ext": "mp4"}
        with YoutubeDL(self.options(quality="720p")) as a, YoutubeDL(self.options(quality="1080p")) as b:
            self.assertNotEqual(a.prepare_filename(info), b.prepare_filename(info))

    def test_mp4_remux_is_before_thumbnail_embedding(self):
        opts = DownloadEngine()._build_yt_dlp_options(False, Path("C:/review"), Path("ffmpeg"), "720p", True)
        keys = [pp["key"] for pp in opts["postprocessors"]]
        self.assertLess(keys.index("FFmpegVideoRemuxer"), keys.index("EmbedThumbnail"))

    def test_audio_never_remuxes_to_video(self):
        keys = [pp["key"] for pp in self.options(True, "192 kbps")["postprocessors"]]
        self.assertNotIn("FFmpegVideoRemuxer", keys)

    def test_title_cannot_escape_destination(self):
        with YoutubeDL(self.options()) as ydl:
            name = ydl.prepare_filename({"title": "../../evil\\name", "id": "safe", "ext": "mp4"})
        self.assertEqual(Path(name).parent, Path("C:/review"))

    def test_only_media_urls_and_known_hosts_are_allowed(self):
        for url in ["http://localhost/watch?v=x", "https://youtube.com.evil.example/watch?v=x", "https://youtube.com/redirect?q=https://evil.example", "https://user:pass@youtube.com/watch?v=x", "https://youtube.com:9000/watch?v=x"]:
            self.assertFalse(SecurityValidator.is_valid_youtube_url(url), url)
        for url in ["https://youtu.be/abc_123", "https://youtube.com/shorts/abc", "https://music.youtube.com/watch?v=x", "https://youtube.com/playlist?list=PL123"]:
            self.assertTrue(SecurityValidator.is_valid_youtube_url(url), url)

    def test_playlist_preview_does_not_extract_every_video(self):
        with patch("yt_dlp.YoutubeDL") as factory:
            factory.return_value.__enter__.return_value.extract_info.return_value = None
            DownloadEngine.extract_metadata_fast("https://youtube.com/playlist?list=PL123")
            opts = factory.call_args.args[0]
            self.assertEqual(opts["extract_flat"], "in_playlist")
            self.assertEqual(opts["playlistend"], 1)
