import unittest
from unittest.mock import MagicMock, patch
import queue
from pathlib import Path

from config.settings import DEFAULT_YOUTUBE_EXTRACTOR_ARGS
from core.downloader import DownloadEngine
from ui.app_window import AppWindow


class TestButtonStateAndPlayerClient(unittest.TestCase):
    def setUp(self):
        with patch.object(AppWindow, "__init__", lambda s: None):
            self.app = AppWindow()
            self.app.download_queue = queue.Queue()
            self.app.is_downloading = False
            self.app._queue_total_items = 0
            self.app._queue_completed_items = 0
            self.app.downloader = MagicMock(spec=DownloadEngine)
            self.app.console_view = MagicMock()
            self.app.progress_widget = MagicMock()
            self.app.download_btn = MagicMock()
            self.app.enqueue_btn = MagicMock()
            self.app.destination_label = MagicMock()
            self.app.download_card = MagicMock()
            self.app.preview_card = MagicMock()
            self.app.after = MagicMock(side_effect=lambda delay, fn: fn() if callable(fn) else None)
            self.app.winfo_exists = MagicMock(return_value=True)

    def test_default_youtube_extractor_args_present_in_downloader_options(self):
        """Verifica que _build_yt_dlp_options incluya player_client: ['ios', 'android', 'web']."""
        engine = DownloadEngine()
        dest = Path("C:/Downloads")
        opts_audio = engine._build_yt_dlp_options(
            is_audio=True,
            destination=dest,
            ffmpeg_dir=dest,
            quality="320 kbps",
        )
        self.assertIn("extractor_args", opts_audio)
        self.assertEqual(opts_audio["extractor_args"], DEFAULT_YOUTUBE_EXTRACTOR_ARGS)
        self.assertEqual(
            opts_audio["extractor_args"]["youtube"]["player_client"],
            ["ios", "android", "web"],
        )

        opts_video = engine._build_yt_dlp_options(
            is_audio=False,
            destination=dest,
            ffmpeg_dir=dest,
            quality="1080p",
        )
        self.assertIn("extractor_args", opts_video)
        self.assertEqual(opts_video["extractor_args"], DEFAULT_YOUTUBE_EXTRACTOR_ARGS)
        self.assertIn("/best", opts_video["format"])

    def test_extract_metadata_fast_uses_extractor_args(self):
        """Verifica que extract_metadata_fast aplique DEFAULT_YOUTUBE_EXTRACTOR_ARGS a YoutubeDL."""
        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl_instance = MagicMock()
            mock_ydl_class.return_value.__enter__.return_value = mock_ydl_instance
            mock_ydl_instance.extract_info.return_value = {
                "title": "Prueba",
                "uploader": "Canal",
                "duration": 180,
                "thumbnail": "http://img.jpg",
            }
            res = DownloadEngine.extract_metadata_fast("https://www.youtube.com/watch?v=jxQHd9Y2JWU")
            self.assertIsNotNone(res)
            call_opts = mock_ydl_class.call_args[0][0]
            self.assertIn("extractor_args", call_opts)
            self.assertEqual(call_opts["extractor_args"], DEFAULT_YOUTUBE_EXTRACTOR_ARGS)

    def test_extract_playlist_urls_uses_extractor_args(self):
        """Verifica que extract_playlist_urls aplique DEFAULT_YOUTUBE_EXTRACTOR_ARGS."""
        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_ydl_instance = MagicMock()
            mock_ydl_class.return_value.__enter__.return_value = mock_ydl_instance
            mock_ydl_instance.extract_info.return_value = {
                "entries": [{"id": "abc12345678", "url": "https://youtube.com/watch?v=abc12345678"}]
            }
            urls = DownloadEngine.extract_playlist_urls("https://www.youtube.com/playlist?list=PL123")
            self.assertEqual(len(urls), 1)
            call_opts = mock_ydl_class.call_args[0][0]
            self.assertIn("extractor_args", call_opts)
            self.assertEqual(call_opts["extractor_args"], DEFAULT_YOUTUBE_EXTRACTOR_ARGS)

    def test_download_btn_disabled_during_download_and_enqueue_btn_enabled(self):
        """Al iniciar descarga: download_btn se deshabilita y enqueue_btn permanece habilitado."""
        dest = Path("C:/Downloads")
        self.app.download_queue.put(("https://youtube.com/watch?v=test1", "MP3", "320 kbps", dest))

        with patch("threading.Thread") as mock_thread:
            self.app._process_next_in_queue(apply_delay=False)
            mock_thread.assert_called_once()
            self.assertTrue(self.app.is_downloading)

            # download_btn debe estar disabled y texto Descargando...
            self.app.download_btn.configure.assert_called_with(
                state="disabled", text="Descargando..."
            )
            # enqueue_btn debe estar normal
            self.app.enqueue_btn.configure.assert_called_with(state="normal")

    def test_start_download_task_blocked_when_already_downloading(self):
        """Si is_downloading es True, start_download_task no añade a la cola ni inicia procesos."""
        self.app.is_downloading = True
        self.app.download_card.get_url.return_value = "https://www.youtube.com/watch?v=blocked"

        with patch.object(self.app, "_add_to_queue") as mock_add, patch.object(
            self.app, "_process_next_in_queue"
        ) as mock_process:
            self.app.start_download_task()
            mock_add.assert_not_called()
            mock_process.assert_not_called()

    def test_enqueue_download_allowed_while_downloading(self):
        """Si is_downloading es True, enqueue_download añade a la cola sin reiniciar el hilo."""
        self.app.is_downloading = True
        self.app.download_card.get_url.return_value = "https://www.youtube.com/watch?v=queued"
        self.app.download_card.get_format.return_value = "MP3"
        self.app.download_card.get_quality.return_value = "320 kbps"
        self.app._get_current_destination = MagicMock(return_value=Path("C:/Downloads"))
        self.app._validate_url = MagicMock(return_value=True)

        with patch.object(self.app, "_add_to_queue") as mock_add, patch.object(
            self.app, "_process_next_in_queue"
        ) as mock_process:
            self.app.enqueue_download()
            mock_add.assert_called_once()
            mock_process.assert_not_called()

    def test_download_btn_reenabled_when_queue_completes(self):
        """Al vaciarse la cola, download_btn vuelve a state='normal' y texto 'Descargar ahora'."""
        self.app.is_downloading = True
        # Cola vacía
        self.app._process_next_in_queue(apply_delay=False)

        self.assertFalse(self.app.is_downloading)
        self.app.download_btn.configure.assert_called_with(
            state="normal", text="Descargar ahora"
        )
        self.app.enqueue_btn.configure.assert_called_with(state="normal")
        self.app.progress_widget.set_completed.assert_called_once()

    def test_antibot_sign_in_bot_error_triggers_retry(self):
        """Verifica que el error 'Sign in to confirm you are not a bot' sea detectado y reintentado."""
        dest = Path("C:/Downloads")
        attempts = 0

        def fake_download(*args, **kwargs):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise Exception("ERROR: [youtube] jxQHd9Y2JWU: Sign in to confirm you're not a bot.")
            return

        self.app.downloader.execute_download.side_effect = fake_download

        with patch("time.sleep") as mock_sleep:
            self.app._run_download_thread(
                url="https://youtube.com/watch?v=jxQHd9Y2JWU",
                fmt="MP3",
                quality="320 kbps",
                destination=dest,
            )

            mock_sleep.assert_called_once()
            self.assertEqual(attempts, 2)
            self.app.after.assert_called_with(0, self.app._on_single_download_success)


if __name__ == "__main__":
    unittest.main()
