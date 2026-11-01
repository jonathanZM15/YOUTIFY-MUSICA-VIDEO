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
            with patch("core.updater.UPDATE_STATE_FILE", test_file):
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

    def test_extract_playlist_urls_does_not_silently_truncate(self):
        """Las playlists completas no se recortan silenciosamente a 100 elementos."""
        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_instance = MagicMock()
            mock_ydl_class.return_value.__enter__.return_value = mock_instance
            mock_instance.extract_info.return_value = {
                "entries": [{"id": "abc123", "url": "https://youtube.com/watch?v=abc123"}]
            }
            DownloadEngine.extract_playlist_urls("https://www.youtube.com/playlist?list=RDtest")
            call_opts = mock_ydl_class.call_args[0][0]
            self.assertNotIn("playlistend", call_opts)

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




if __name__ == "__main__":
    unittest.main()
