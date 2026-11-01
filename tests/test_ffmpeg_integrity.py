import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from core.ffmpeg_manager import FFmpegManager


class TestFFmpegIntegrity(unittest.TestCase):
    def archive(self, second=True):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            archive.writestr("release/bin/ffmpeg.exe", b"MZ" + b"a" * 2048)
            if second: archive.writestr("release/bin/ffprobe.exe", b"MZ" + b"b" * 2048)
        return stream.getvalue()

    def test_invalid_hash_does_not_install_executables(self):
        with tempfile.TemporaryDirectory() as tmp, patch("core.ffmpeg_manager.APPDATA_FFMPEG_DIR", Path(tmp)), patch("core.ffmpeg_manager.FFMPEG_EXPECTED_SHA256", "0" * 64), patch("urllib.request.urlopen", return_value=io.BytesIO(self.archive())):
            with self.assertRaisesRegex(RuntimeError, "SHA-256"):
                FFmpegManager._download_fallback(None)
            self.assertFalse(list(Path(tmp).glob("*.exe")))

    def test_missing_probe_does_not_leave_half_an_installation(self):
        data = self.archive(False)
        with tempfile.TemporaryDirectory() as tmp, patch("core.ffmpeg_manager.APPDATA_FFMPEG_DIR", Path(tmp)), patch("core.ffmpeg_manager.FFMPEG_EXPECTED_SHA256", hashlib.sha256(data).hexdigest()), patch("urllib.request.urlopen", return_value=io.BytesIO(data)):
            with self.assertRaises(RuntimeError): FFmpegManager._download_fallback(None)
            self.assertFalse(list(Path(tmp).iterdir()))

    def test_verified_pair_is_installed(self):
        data = self.archive()
        with tempfile.TemporaryDirectory() as tmp, patch("core.ffmpeg_manager.APPDATA_FFMPEG_DIR", Path(tmp)), patch("core.ffmpeg_manager.FFMPEG_EXPECTED_SHA256", hashlib.sha256(data).hexdigest()), patch("urllib.request.urlopen", return_value=io.BytesIO(data)):
            self.assertEqual(FFmpegManager._download_fallback(None), Path(tmp))
            self.assertTrue((Path(tmp)/"ffmpeg.exe").is_file())
            self.assertTrue((Path(tmp)/"ffprobe.exe").is_file())
            self.assertFalse(list(Path(tmp).glob("*.tmp")))
