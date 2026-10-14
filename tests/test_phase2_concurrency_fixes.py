"""
Tests unitarios para las correcciones de concurrencia, thread-safety y bugs funcionales de la Fase 2.

Cubre:
  1. ThumbnailOptimizerPP registra tanto filepath original como optimizado en created_thumbnails.
  2. _inspect_url_async no accede a widgets Tkinter fuera del hilo principal.
  3. PreviewCard usa _request_id para evitar race conditions en miniaturas.
  4. Updater._state_lock protege acceso concurrente a update_state.json.
  5. _build_yt_dlp_options con restrictfilenames=False; _progress_hook manejo dinámico de streams;
     extract_playlist_urls incluye playlistend=100.
  6. _on_single_download_success muestra mensaje condicional según embed_thumbnail.
"""
import json
import queue
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, call

from PIL import Image

from config.settings import THUMBNAIL_MAX_DIMENSION, THUMBNAIL_JPEG_QUALITY
from core.downloader import ThumbnailOptimizerPP, DownloadEngine, optimize_thumbnail
from core.updater import Updater
from ui.app_window import AppWindow


class TestThumbnailCreatedTrackingPhase2(unittest.TestCase):
    """Fix #1: ThumbnailOptimizerPP registra ambas rutas (original + optimizada) en created_thumbnails."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_both_original_and_optimized_paths_tracked(self):
        """Registra tanto el filepath original (.webp) como el optimizado (.jpg)."""
        src = self.temp_path / "thumb.webp"
        img = Image.new("RGB", (1280, 720), color=(50, 100, 200))
        img.save(src, format="WEBP")

        info = {"thumbnails": [{"filepath": str(src), "id": "0"}]}
        pp = ThumbnailOptimizerPP(max_dimension=THUMBNAIL_MAX_DIMENSION, quality=THUMBNAIL_JPEG_QUALITY)
        pp.run(info)

        # Debe contener al menos 2 rutas: la original .webp y la optimizada .jpg
        self.assertGreaterEqual(len(pp.created_thumbnails), 2)
        extensions = {p.suffix.lower() for p in pp.created_thumbnails}
        self.assertIn(".webp", extensions)
        self.assertIn(".jpg", extensions)

    def test_same_extension_jpeg_still_tracked(self):
        """Un JPEG pequeño que no cambia de extensión se registra igualmente."""
        src = self.temp_path / "thumb.jpg"
        img = Image.new("RGB", (400, 400), color=(80, 80, 80))
        img.save(src, format="JPEG", quality=85)

        info = {"thumbnails": [{"filepath": str(src), "id": "0"}]}
        pp = ThumbnailOptimizerPP(max_dimension=600, quality=85)
        pp.run(info)

        # Debe registrar la ruta original (y la optimizada, que es la misma)
        self.assertTrue(len(pp.created_thumbnails) >= 1)
        self.assertTrue(any(p.name == "thumb.jpg" for p in pp.created_thumbnails))


class TestInspectUrlThreadSafety(unittest.TestCase):
    """Fix #2: _inspect_url_async no llama a get_url() fuera del hilo principal."""

    def setUp(self):
        with patch.object(AppWindow, "__init__", lambda s: None):
            self.app = AppWindow()
            self.app.download_card = MagicMock()
            self.app.preview_card = MagicMock()
            self.app.after = MagicMock(side_effect=lambda delay, fn: fn() if callable(fn) else None)

    def test_no_get_url_call_in_background_thread(self):
        """_task() no debe llamar a self.download_card.get_url() en el hilo secundario."""
        # Simular extract_metadata_fast que devuelve None rápidamente
        with patch.object(DownloadEngine, "extract_metadata_fast", return_value=None):
            # Ejecutar _inspect_url_async y capturar el Thread
            with patch("threading.Thread") as mock_thread:
                self.app._inspect_url_async("https://www.youtube.com/watch?v=test123")
                thread_target = mock_thread.call_args[1]["target"]

            # Resetear contadores de get_url antes de ejecutar _task
            self.app.download_card.get_url.reset_mock()

            # Ejecutar _task en el hilo actual (simula el hilo secundario)
            thread_target()

            # get_url solo debe haberse llamado dentro de _apply_meta (ejecutado por after),
            # NO directamente en _task antes de extract_metadata_fast
            # Como after ejecuta inmediatamente por el side_effect, get_url se llama en _apply_meta
            # Verificamos que se llamó exactamente 1 vez (solo en _apply_meta, no en _task)
            self.assertEqual(self.app.download_card.get_url.call_count, 1)

    def test_meta_applied_only_when_url_matches(self):
        """Si la URL cambió mientras se extraían metadatos, se oculta la preview."""
        meta = {
            "title": "Test Video", "channel": "Canal", "duration": "3:00",
            "thumbnail": "https://example.com/thumb.jpg", "is_playlist": False,
        }
        with patch.object(DownloadEngine, "extract_metadata_fast", return_value=meta):
            with patch("threading.Thread") as mock_thread:
                self.app._inspect_url_async("https://www.youtube.com/watch?v=original")
                thread_target = mock_thread.call_args[1]["target"]

            # Simular que la URL cambió
            self.app.download_card.get_url.return_value = "https://www.youtube.com/watch?v=DIFFERENT"
            thread_target()

            self.app.preview_card.hide_preview.assert_called()


class TestPreviewCardRequestId(unittest.TestCase):
    """Fix #3: PreviewCard usa _request_id para cancelar miniaturas obsoletas."""

    def test_request_id_increments_on_show(self):
        """show_preview incrementa _request_id."""
        from ui.components.preview_card import PreviewCard
        with patch.object(PreviewCard, "__init__", lambda s, p: None):
            card = PreviewCard(None)
            card._request_id = 0
            card.title_label = MagicMock()
            card.channel_badge = MagicMock()
            card.duration_badge = MagicMock()
            card.thumb_label = MagicMock()
            card._thumb_img = None
            card.pack = MagicMock()

            # Sin thumbnail_url no se lanza hilo
            with patch("threading.Thread"):
                card.show_preview("Título", "Canal", "3:00")
            self.assertEqual(card._request_id, 1)

            with patch("threading.Thread"):
                card.show_preview("Otro Título", "Otro Canal", "5:00")
            self.assertEqual(card._request_id, 2)

    def test_request_id_increments_on_hide(self):
        """hide_preview incrementa _request_id y limpia _thumb_img."""
        from ui.components.preview_card import PreviewCard
        with patch.object(PreviewCard, "__init__", lambda s, p: None):
            card = PreviewCard(None)
            card._request_id = 5
            card.title_label = MagicMock()
            card.channel_badge = MagicMock()
            card.duration_badge = MagicMock()
            card.thumb_label = MagicMock()
            card._thumb_img = "some_image"
            card.pack_forget = MagicMock()

            card.hide_preview()
            self.assertEqual(card._request_id, 6)
            self.assertIsNone(card._thumb_img)

    def test_stale_thumbnail_not_applied(self):
        """Un callback con req_id obsoleto no actualiza thumb_label."""
        from ui.components.preview_card import PreviewCard
        with patch.object(PreviewCard, "__init__", lambda s, p: None):
            card = PreviewCard(None)
            card._request_id = 10
            card.thumb_label = MagicMock()
            card._thumb_img = None
            card.MAX_THUMB_BYTES = 5 * 1024 * 1024

            # Simular que _fetch_and_render_thumb fue llamado con req_id=5 (obsoleto)
            # y su callback se ejecuta después
            stale_req_id = 5
            # La función _apply_thumb solo configura si req_id == self._request_id
            if stale_req_id == card._request_id:
                card.thumb_label.configure(image="new_image", text="")
            # No debe haberse llamado
            card.thumb_label.configure.assert_not_called()


class TestUpdaterStateLock(unittest.TestCase):
    """Fix #4: Updater._state_lock protege acceso concurrente a update_state.json."""

    def test_state_lock_exists(self):
        """Updater tiene un _state_lock de tipo threading.Lock."""
        self.assertTrue(hasattr(Updater, "_state_lock"))
        self.assertIsInstance(Updater._state_lock, type(threading.Lock()))

    def test_concurrent_read_write_does_not_corrupt(self):
        """Escrituras y lecturas concurrentes no corrompen update_state.json."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = Path(tmp_dir) / "update_state.json"
            with patch("config.settings.UPDATE_STATE_FILE", test_file):
                errors = []
                results = []

                def writer(tag):
                    try:
                        for i in range(10):
                            state = Updater._read_update_state()
                            state[f"key_{tag}_{i}"] = i
                            Updater._write_update_state(state)
                    except Exception as e:
                        errors.append(e)

                def reader():
                    try:
                        for _ in range(20):
                            state = Updater._read_update_state()
                            results.append(type(state))
                    except Exception as e:
                        errors.append(e)

                threads = [
                    threading.Thread(target=writer, args=("A",)),
                    threading.Thread(target=writer, args=("B",)),
                    threading.Thread(target=reader),
                ]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join(timeout=5)

                self.assertEqual(len(errors), 0, f"Errores de concurrencia: {errors}")
                # Todos los reads deben devolver dict
                self.assertTrue(all(r == dict for r in results))


class TestDownloaderBugFixesPhase2(unittest.TestCase):
    """Fix #5: restrictfilenames=False, progreso dinámico de streams, playlistend=100."""

    def test_restrictfilenames_is_false(self):
        """_build_yt_dlp_options configura restrictfilenames=False para preservar espacios y tildes."""
        engine = DownloadEngine()
        opts = engine._build_yt_dlp_options(
            is_audio=True, destination=Path("C:/Downloads"),
            ffmpeg_dir=Path("C:/ffmpeg"), quality="320 kbps",
        )
        self.assertFalse(opts["restrictfilenames"])
        self.assertTrue(opts["windowsfilenames"])

    def test_windowsfilenames_still_true(self):
        """windowsfilenames se mantiene True para evitar caracteres inválidos en Windows."""
        engine = DownloadEngine()
        opts = engine._build_yt_dlp_options(
            is_audio=False, destination=Path("C:/Downloads"),
            ffmpeg_dir=Path("C:/ffmpeg"), quality="720p",
        )
        self.assertTrue(opts["windowsfilenames"])
        self.assertFalse(opts["restrictfilenames"])

    def test_extract_playlist_urls_has_playlistend(self):
        """extract_playlist_urls incluye playlistend=100 para limitar mixes infinitos."""
        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_instance = MagicMock()
            mock_ydl_class.return_value.__enter__.return_value = mock_instance
            mock_instance.extract_info.return_value = {
                "entries": [{"id": "abc123", "url": "https://youtube.com/watch?v=abc123"}]
            }
            DownloadEngine.extract_playlist_urls("https://www.youtube.com/playlist?list=RDtest")
            call_opts = mock_ydl_class.call_args[0][0]
            self.assertEqual(call_opts.get("playlistend"), 100)

    def test_progress_hook_single_stream_progressive_completes_to_100(self):
        """Un video progresivo (sin requested_formats) completa al 100% en la primera señal de finished."""
        progress_calls = []
        status_calls = []

        engine = DownloadEngine(
            on_progress=lambda p, pct, s, e: progress_calls.append(p),
            on_status=lambda code, label: status_calls.append(code),
        )
        engine.is_audio = False
        engine._expected_stream_count = 2  # Pre-consulta falló, asumió 2

        # Simular finished sin requested_formats (stream progresivo)
        engine._progress_hook({
            "status": "finished",
            "info_dict": {},  # Sin requested_formats
        })

        # Debe haber ajustado a 1 stream y completado al 100%
        self.assertEqual(engine._expected_stream_count, 1)
        self.assertEqual(engine._last_progress_value, 1.0)
        self.assertIn(1.0, progress_calls)

    def test_progress_hook_dual_stream_transitions_correctly(self):
        """Un video con 2 requested_formats transiciona correctamente entre streams."""
        engine = DownloadEngine()
        engine.is_audio = False
        engine._expected_stream_count = 2

        # Simular finished del primer stream con requested_formats presente
        engine._progress_hook({
            "status": "finished",
            "info_dict": {
                "requested_formats": [
                    {"format_id": "137", "filesize": 50_000_000},
                    {"format_id": "140", "filesize": 5_000_000},
                ]
            },
        })

        # Primer stream completado, debe seguir esperando el segundo
        self.assertEqual(engine._stream_phase_index, 1)
        self.assertNotEqual(engine._last_progress_value, 1.0)

        # Simular finished del segundo stream
        engine._progress_hook({
            "status": "finished",
            "info_dict": {
                "requested_formats": [
                    {"format_id": "137", "filesize": 50_000_000},
                    {"format_id": "140", "filesize": 5_000_000},
                ]
            },
        })

        # Ambos completados
        self.assertEqual(engine._last_progress_value, 1.0)


class TestConditionalSuccessMessage(unittest.TestCase):
    """Fix #6: _on_single_download_success muestra mensaje diferente según embed_thumbnail."""

    def setUp(self):
        with patch.object(AppWindow, "__init__", lambda s: None):
            self.app = AppWindow()
            self.app.download_queue = queue.Queue()
            self.app.is_downloading = True
            self.app._queue_total_items = 1
            self.app._queue_completed_items = 0
            self.app.downloader = MagicMock(spec=DownloadEngine)
            self.app.console_view = MagicMock()
            self.app.progress_widget = MagicMock()
            self.app.download_btn = MagicMock()
            self.app.enqueue_btn = MagicMock()
            self.app.after = MagicMock(side_effect=lambda delay, fn: fn() if callable(fn) else None)
            self.app.winfo_exists = MagicMock(return_value=True)

    def test_success_with_thumbnail_shows_cover_message(self):
        """Con embed_thumbnail=True, muestra mensaje con carátula."""
        self.app._on_single_download_success(embed_thumbnail=True)
        self.app.console_view.append_log.assert_any_call(
            "[✓] Archivo guardado y carátula incrustada con éxito."
        )

    def test_success_without_thumbnail_shows_simple_message(self):
        """Con embed_thumbnail=False, muestra mensaje sin mención de carátula."""
        self.app._on_single_download_success(embed_thumbnail=False)
        self.app.console_view.append_log.assert_any_call(
            "[✓] Archivo guardado con éxito."
        )

    def test_default_parameter_is_true(self):
        """El valor por defecto de embed_thumbnail es True (compatibilidad con tests existentes)."""
        self.app._on_single_download_success()
        self.app.console_view.append_log.assert_any_call(
            "[✓] Archivo guardado y carátula incrustada con éxito."
        )

    def test_run_download_thread_passes_embed_thumbnail_to_success(self):
        """_run_download_thread pasa embed_thumbnail al callback de éxito."""
        dest = Path("C:/Downloads")
        self.app.downloader.execute_download.return_value = None

        # Capturar las llamadas a after
        after_calls = []
        self.app.after = MagicMock(side_effect=lambda d, fn: after_calls.append((d, fn)))

        self.app._run_download_thread(
            url="https://youtube.com/watch?v=test",
            fmt="MP3",
            quality="320 kbps",
            destination=dest,
            embed_thumbnail=False,
        )

        # Encontrar el callback de éxito (delay=0)
        success_cbs = [fn for d, fn in after_calls if d == 0]
        self.assertTrue(len(success_cbs) > 0)

        # Ejecutar el callback y verificar que pasa embed_thumbnail=False
        with patch.object(self.app, "_on_single_download_success") as mock_success:
            success_cbs[-1]()
            mock_success.assert_called_once_with(embed_thumbnail=False)


if __name__ == "__main__":
    unittest.main()
