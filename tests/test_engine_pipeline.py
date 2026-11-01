"""Real download/postprocessing pipeline using local synthetic media, no YouTube access."""
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch
from PIL import Image
from mutagen.mp3 import MP3
from yt_dlp import YoutubeDL as RealYoutubeDL
from config.settings import BUNDLED_FFMPEG_DIR
from core.downloader import DownloadEngine, DownloadCancelled


@unittest.skipUnless((BUNDLED_FFMPEG_DIR / "ffmpeg.exe").is_file(), "Run prepare_components.py for media integration tests")
class TestEnginePipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root = Path(cls.tmp.name)
        cls.source = cls.root / "fixture.webm"
        cls.thumbnail = cls.root / "cover.png"
        Image.new("RGBA", (850, 850), (30, 190, 170, 255)).save(cls.thumbnail)
        subprocess.run([str(BUNDLED_FFMPEG_DIR / "ffmpeg.exe"), "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "color=c=teal:s=320x180:r=10", "-f", "lavfi", "-i", "sine=frequency=440",
            "-t", "0.6", "-c:v", "libvpx-vp9", "-c:a", "libopus", str(cls.source)],
            check=True, capture_output=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        # Exercise the HTTP path used by real downloads. yt-dlp's optional
        # file:// handler can retain source handles until garbage collection,
        # which prevents Windows runners from deleting the fixture directory.
        class Handler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(cls.root), **kwargs)
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        cls.base_url = f"http://127.0.0.1:{server.server_port}"
        def close_server():
            server.shutdown()
            server.server_close()
            worker.join(3)
        cls.addClassCleanup(close_server)

    def run_engine(self, fmt, video_id, cover):
        source, thumbnail = self.base_url+"/fixture.webm", self.base_url+"/cover.png"
        class FixtureYoutubeDL(RealYoutubeDL):
            def extract_info(self, url, download=True, *args, **kwargs):
                info = {"id": video_id, "title": "Same fixture title", "extractor": "fixture", "extractor_key": "Fixture",
                    "webpage_url": url, "duration": 0.6, "uploader": "Youtify tests", "thumbnail": thumbnail,
                    "thumbnails": [{"url": thumbnail, "id": "cover", "ext": "png"}],
                    "formats": [{"format_id": "test", "url": source, "ext": "webm",
                        "vcodec": "vp9", "acodec": "opus", "height": 180, "width": 320}]}
                return self.process_ie_result(info, download=download)
        dest = self.root / ("audio" if fmt.startswith("MP3") else "video")
        with patch("yt_dlp.YoutubeDL", FixtureYoutubeDL):
            return DownloadEngine().execute_download(f"https://youtube.com/watch?v={video_id}", fmt,
                "192 kbps" if fmt.startswith("MP3") else "720p", dest, cover)

    def test_mp3_conversion_and_real_embedded_cover(self):
        result = self.run_engine("MP3 (audio)", "audio-cover", True)
        path = Path(result["filepath"])
        self.assertEqual(path.suffix, ".mp3")
        tags = MP3(path)
        self.assertTrue(tags.tags.getall("APIC"))
        with Image.open(__import__("io").BytesIO(tags.tags.getall("APIC")[0].data)) as image:
            self.assertLessEqual(max(image.size), 600)
        self.assertTrue(tags.tags.getall("TIT2"))

    def test_mp3_without_cover_leaves_no_thumbnail_files(self):
        result = self.run_engine("MP3 (audio)", "audio-no-cover", False)
        self.assertFalse(MP3(result["filepath"]).tags.getall("APIC"))
        self.assertFalse(list(Path(result["filepath"]).parent.glob("*.png")))

    def test_webm_fallback_becomes_real_mp4(self):
        result = self.run_engine("MP4 (video)", "video-remux", True)
        path = Path(result["filepath"])
        self.assertEqual(path.suffix, ".mp4")
        probe = subprocess.run([str(BUNDLED_FFMPEG_DIR / "ffprobe.exe"), "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)],
            capture_output=True, text=True, check=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        data = json.loads(probe.stdout)
        self.assertIn("mp4", data["format"]["format_name"])
        self.assertTrue(any(s["codec_type"] == "audio" for s in data["streams"]))
        self.assertTrue(any(s["codec_type"] == "video" for s in data["streams"]))

    def test_same_title_distinct_videos_both_exist(self):
        first = self.run_engine("MP3 (audio)", "unique-one", False)
        second = self.run_engine("MP3 (audio)", "unique-two", False)
        self.assertNotEqual(first["filepath"], second["filepath"])
        self.assertTrue(Path(first["filepath"]).is_file())
        self.assertTrue(Path(second["filepath"]).is_file())

    def test_cancel_before_download_never_reports_success(self):
        engine = DownloadEngine()
        engine.cancel()
        with self.assertRaises(DownloadCancelled):
            engine.execute_download("https://youtube.com/watch?v=test", "MP3", "192 kbps", self.root)
