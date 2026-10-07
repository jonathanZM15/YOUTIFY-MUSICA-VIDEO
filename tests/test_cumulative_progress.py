import unittest
from unittest.mock import MagicMock, patch
import queue
from pathlib import Path

from ui.app_window import AppWindow
from core.downloader import DownloadEngine


class TestCumulativeProgress(unittest.TestCase):
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

    def test_single_video_progress_flow(self):
        """(a) Un solo video: debe comportarse de 0% a 100%, un item = toda la barra."""
        dest = Path("C:/Downloads")
        with patch.object(DownloadEngine, "extract_playlist_urls", return_value=[]):
            self.app._add_to_queue("https://youtube.com/watch?v=single", "MP3", "320 kbps", dest)

        self.assertEqual(self.app._queue_total_items, 1)
        self.assertEqual(self.app._queue_completed_items, 0)

        # Simular progreso al 50%
        self.app._handle_progress(0.5, "50.0%", "10.0MiB/s", "00:05")
        self.app.progress_widget.set_progress.assert_called_with(0.5)
        # Badge en video único muestra estado simplificado sin 'video 1 de 1'
        self.app.progress_widget.set_active_download.assert_called_with(1, 1)

        # Simular progreso al 100%
        self.app._handle_progress(1.0, "100.0%", "10.0MiB/s", "00:00")
        self.app.progress_widget.set_progress.assert_called_with(1.0)

        # Finalizar elemento
        with patch.object(self.app, "_process_next_in_queue") as mock_next:
            self.app._on_single_download_success()
            self.assertEqual(self.app._queue_completed_items, 1)
            mock_next.assert_called_with(apply_delay=True)

    def test_multi_video_cumulative_progress_and_badge(self):
        """(b) Playlist de 5 videos: progreso continuo acumulativo y badge 'video X de N'."""
        dest = Path("C:/Downloads")
        urls = [f"https://youtube.com/watch?v={i}" for i in range(1, 6)]
        with patch.object(DownloadEngine, "extract_playlist_urls", return_value=urls):
            self.app._add_to_queue("https://youtube.com/playlist?list=5items", "MP3", "320 kbps", dest)

        self.assertEqual(self.app._queue_total_items, 5)
        self.assertEqual(self.app._queue_completed_items, 0)
        self.assertEqual(self.app.download_queue.qsize(), 5)

        # ── Video 1 (items completados = 0) ──
        # Video 1 al 50%: global = (0 + 0.5) / 5 = 0.10 (10%)
        self.app._handle_progress(0.5, "50.0%", "10.0MiB/s", "")
        self.app.progress_widget.set_progress.assert_called_with(0.10)
        self.app.progress_widget.set_active_download.assert_called_with(1, 5)

        # Video 1 termina
        self.app._queue_completed_items += 1  # 1 completado
        self.assertEqual(self.app._queue_completed_items, 1)

        # ── Video 2 (items completados = 1) ──
        # Video 2 al inicio (0%): global = (1 + 0.0) / 5 = 0.20 (20%)
        self.app._handle_progress(0.0, "0.0%", "12.0MiB/s", "")
        self.app.progress_widget.set_progress.assert_called_with(0.20)
        self.app.progress_widget.set_active_download.assert_called_with(2, 5)

        # Video 2 al 50%: global = (1 + 0.5) / 5 = 0.30 (30%)
        self.app._handle_progress(0.5, "50.0%", "12.0MiB/s", "")
        self.app.progress_widget.set_progress.assert_called_with(0.30)
        self.app.progress_widget.set_active_download.assert_called_with(2, 5)

        # Video 2 termina
        self.app._queue_completed_items += 1  # 2 completados

        # ── Video 4 (items completados = 3) ──
        self.app._queue_completed_items = 3
        # Video 4 al 60%: global = (3 + 0.6) / 5 = 0.72 (72%)
        self.app._handle_progress(0.6, "60.0%", "15.0MiB/s", "")
        self.app.progress_widget.set_progress.assert_called_with(0.72)
        self.app.progress_widget.set_active_download.assert_called_with(4, 5)

        # ── Video 5 (items completados = 4) ──
        self.app._queue_completed_items = 4
        # Video 5 al 100%: global = (4 + 1.0) / 5 = 1.0 (100%)
        self.app._handle_progress(1.0, "100.0%", "15.0MiB/s", "")
        self.app.progress_widget.set_progress.assert_called_with(1.0)
        self.app.progress_widget.set_active_download.assert_called_with(5, 5)


    def test_dynamic_enqueue_while_downloading(self):
        """Si se agregan elementos con is_downloading == True, se incrementa _queue_total_items."""
        dest = Path("C:/Downloads")
        with patch.object(DownloadEngine, "extract_playlist_urls", return_value=[]):
            self.app._add_to_queue("https://youtube.com/watch?v=1", "MP3", "320 kbps", dest)
        self.assertEqual(self.app._queue_total_items, 1)

        # Simular que ya está descargando
        self.app.is_downloading = True

        # Agregar otro video mientras descarga
        with patch.object(DownloadEngine, "extract_playlist_urls", return_value=[]):
            self.app._add_to_queue("https://youtube.com/watch?v=2", "MP3", "320 kbps", dest)
        self.assertEqual(self.app._queue_total_items, 2)

        # Agregar una playlist de 3 videos mientras descarga
        more_urls = [f"https://youtube.com/watch?v=extra_{i}" for i in range(3)]
        with patch.object(DownloadEngine, "extract_playlist_urls", return_value=more_urls):
            self.app._add_to_queue("https://youtube.com/playlist?list=more", "MP3", "320 kbps", dest)
        self.assertEqual(self.app._queue_total_items, 5)

    def test_queue_completed_resets_counters(self):
        """Al vaciar la cola, se resetean los contadores a 0 tras llamar a set_completed()."""
        self.app._queue_total_items = 5
        self.app._queue_completed_items = 5
        self.app.is_downloading = True
        # download_queue está vacía
        self.app._process_next_in_queue()

        self.assertFalse(self.app.is_downloading)
        self.app.progress_widget.set_completed.assert_called_once()
        self.assertEqual(self.app._queue_total_items, 0)
        self.assertEqual(self.app._queue_completed_items, 0)

    def test_definitive_failure_counts_as_processed(self):
        """Un fallo definitivo incrementa _queue_completed_items para mantener avance de cola."""
        self.app._queue_total_items = 3
        self.app._queue_completed_items = 1

        self.app._on_item_failed_definitively()
        self.assertEqual(self.app._queue_completed_items, 2)
        # Debe haber actualizado la barra al 66.7% (2 / 3)
        self.app.progress_widget.set_progress.assert_called_with(2 / 3)

    def test_progress_bar_widget_simplified_badge_texts(self):
        """Verifica que ProgressBarWidget formatea exclusivamente los 2 estados solicitados."""
        from ui.components.progress_bar import ProgressBarWidget
        from ui.theme import Colors

        with patch.object(ProgressBarWidget, "__init__", lambda s, p: None):
            widget = ProgressBarWidget(None)
            widget.status_badge = MagicMock()
            widget.progress_bar = MagicMock()

            # 1. Caso video único (total=1) -> "⚡ Descargando..."
            widget.set_active_download(1, 1)
            widget.status_badge.configure.assert_called_with(
                text="⚡ Descargando...",
                text_color=Colors.STATUS_ACTIVE_TEXT,
            )

            # 2. Caso playlist / cola (total > 1): elemento 4 de 8 -> "⚡ Descargando 4 de 8"
            widget.set_active_download(4, 8)
            widget.status_badge.configure.assert_called_with(
                text="⚡ Descargando 4 de 8",
                text_color=Colors.STATUS_ACTIVE_TEXT,
            )

            # 3. Caso fase de conversión -> debe mantener "⚡ Descargando 4 de 8"
            widget.set_converting(4, 8)
            widget.status_badge.configure.assert_called_with(
                text="⚡ Descargando 4 de 8",
                text_color=Colors.STATUS_ACTIVE_TEXT,
            )

    def test_mixed_audio_video_queue(self):
        """Prueba una cola mixta de audios (MP3) y videos (MP4) confirmando el texto neutral."""
        from ui.components.progress_bar import ProgressBarWidget
        from ui.theme import Colors

        dest = Path("C:/Downloads")
        # Encolar 1 audio MP3 y 1 video MP4
        with patch.object(DownloadEngine, "extract_playlist_urls", return_value=[]):
            self.app._add_to_queue("https://youtube.com/watch?v=audio1", "MP3 (audio)", "320 kbps", dest)
            self.app.is_downloading = True
            self.app._add_to_queue("https://youtube.com/watch?v=video2", "MP4 (video)", "1080p (FHD)", dest)

        self.assertEqual(self.app._queue_total_items, 2)

        with patch.object(ProgressBarWidget, "__init__", lambda s, p: None):
            widget = ProgressBarWidget(None)
            widget.status_badge = MagicMock()
            widget.progress_bar = MagicMock()

            # Descarga de audio (elemento 1 de 2)
            widget.set_active_download(1, 2)
            widget.status_badge.configure.assert_called_with(
                text="⚡ Descargando 1 de 2",
                text_color=Colors.STATUS_ACTIVE_TEXT,
            )

            # Conversión de audio (elemento 1 de 2)
            widget.set_converting(1, 2)
            widget.status_badge.configure.assert_called_with(
                text="⚡ Descargando 1 de 2",
                text_color=Colors.STATUS_ACTIVE_TEXT,
            )

            # Descarga de video (elemento 2 de 2)
            widget.set_active_download(2, 2)
            widget.status_badge.configure.assert_called_with(
                text="⚡ Descargando 2 de 2",
                text_color=Colors.STATUS_ACTIVE_TEXT,
            )

            # Fusión de video (elemento 2 de 2)
            widget.set_converting(2, 2)
            widget.status_badge.configure.assert_called_with(
                text="⚡ Descargando 2 de 2",
                text_color=Colors.STATUS_ACTIVE_TEXT,
            )

            # Completado general
            widget.set_completed()
            widget.status_badge.configure.assert_called_with(
                text="✨ ¡Descarga completada con éxito!",
                text_color=Colors.STATUS_SUCCESS_TEXT,
            )


if __name__ == "__main__":
    unittest.main()
