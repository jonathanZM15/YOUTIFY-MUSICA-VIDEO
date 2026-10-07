import unittest
from unittest.mock import MagicMock
from pathlib import Path

from core.downloader import DownloadEngine, clean_ansi
from ui.components.progress_bar import ProgressBarWidget, _clean_text as clean_pb_text
from ui.components.console_view import ConsoleView, _ANSI_RE as CONSOLE_ANSI_RE
from ui.app_window import _clean_text as clean_app_text


class TestAnsiSanitization(unittest.TestCase):
    def setUp(self):
        self.dirty_samples = [
            ("\x1b[0;32m15.51MiB/s\x1b[0m", "15.51MiB/s"),
            ("15.51MiB/s\x1b[0m", "15.51MiB/s"),
            ("\x1b[0;33m00:15\x1b[0m", "00:15"),
            ("\x1b[1;36m99.5%\x1b[0m", "99.5%"),
            ("\x1b[KDescargando datos...\x1b[0m", "Descargando datos..."),
            ("Error HTTP 403: \x1b[31mForbidden\x1b[0m", "Error HTTP 403: Forbidden"),
        ]

    def test_clean_ansi_function(self):
        for dirty, expected in self.dirty_samples:
            self.assertEqual(clean_ansi(dirty), expected)

    def test_progress_bar_clean_text(self):
        for dirty, expected in self.dirty_samples:
            self.assertEqual(clean_pb_text(dirty), expected)

    def test_console_view_ansi_regex(self):
        for dirty, expected in self.dirty_samples:
            self.assertEqual(CONSOLE_ANSI_RE.sub("", dirty).strip(), expected)

    def test_app_window_clean_text(self):
        for dirty, expected in self.dirty_samples:
            self.assertEqual(clean_app_text(dirty), expected)

    def test_build_yt_dlp_options_color_never(self):
        engine = DownloadEngine()
        opts = engine._build_yt_dlp_options(
            is_audio=True,
            destination=Path("C:/dummy"),
            ffmpeg_dir=Path("C:/dummy/ffmpeg"),
            quality="320 kbps",
        )
        self.assertEqual(opts.get("color"), "never")

    def test_progress_hook_cleans_dirty_ytdlp_strings(self):
        received_progress = []
        received_logs = []

        def on_prog(prog, pct, speed, eta):
            received_progress.append((prog, pct, speed, eta))

        def on_log(msg):
            received_logs.append(msg)

        engine = DownloadEngine(on_progress=on_prog, on_log=on_log)
        engine.is_audio = True

        dirty_data = {
            "status": "downloading",
            "downloaded_bytes": 5000,
            "total_bytes": 10000,
            "_percent_str": "\x1b[0;32m 50.0%\x1b[0m",
            "_speed_str": "\x1b[0;32m12.45MiB/s\x1b[0m",
            "_eta_str": "\x1b[0;33m00:03\x1b[0m",
        }

        engine._progress_hook(dirty_data)

        self.assertEqual(len(received_progress), 1)
        prog, pct, speed, eta = received_progress[0]
        self.assertEqual(pct, "50.0%")
        self.assertEqual(speed, "12.45MiB/s")
        self.assertEqual(eta, "00:03")
        self.assertNotIn("\x1b", pct)
        self.assertNotIn("\x1b", speed)
        self.assertNotIn("\x1b", eta)

        # Verificar que el mensaje en el log también está limpio
        self.assertTrue(len(received_logs) >= 1)
        last_log = received_logs[-1]
        self.assertNotIn("\x1b", last_log)
        self.assertIn("12.45MiB/s", last_log)


if __name__ == "__main__":
    unittest.main()
