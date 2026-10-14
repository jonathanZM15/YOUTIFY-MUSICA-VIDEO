"""
Tests unitarios para las mejoras y refactorizaciones de la Fase 3:
1. Atomicidad real en Updater (_update_state).
2. Filtrado inteligente de Radio/Mixes autogenerados en extract_playlist_urls.
3. Deduplicación de ANSI Regex y clean_ansi manteniendo compatibilidad.
4. Selector de carpeta personalizada (_custom_destination, _choose_custom_folder, change_folder_btn, limpieza de execute_download).
5. Documentación y workflow CI/CD (versión v1.0.9 y paso de tests).
"""
import json
import queue
import re
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from config.settings import MUSIC_DIR, VIDEO_DIR
import core.downloader as downloader_mod
import ui.app_window as app_window_mod
import ui.components.console_view as console_view_mod
import ui.components.progress_bar as progress_bar_mod
from core.downloader import ANSI_ESCAPE_RE, DownloadEngine, clean_ansi
from core.updater import Updater
from ui.app_window import AppWindow


class TestUpdaterAtomicStatePhase3(unittest.TestCase):
    """Test #1: Atomicidad real en core/updater.py con _update_state."""

    def test_update_state_writes_and_returns_updated_dict(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = Path(tmp_dir) / "update_state.json"
            with patch("core.updater.UPDATE_STATE_FILE", test_file):
                # Inicializar con clave previa
                Updater._write_update_state({"initial_key": "val1"})

                res = Updater._update_state(new_key="val2", count=42)
                self.assertEqual(res["initial_key"], "val1")
                self.assertEqual(res["new_key"], "val2")
                self.assertEqual(res["count"], 42)

                # Verificar lectura fresca de disco
                on_disk = Updater._read_update_state()
                self.assertEqual(on_disk, res)

    def test_postpone_update_uses_update_state(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = Path(tmp_dir) / "update_state.json"
            with patch("core.updater.UPDATE_STATE_FILE", test_file):
                Updater._write_update_state({"existing_flag": True})
                Updater.postpone_update("v1.2.0", hours=12)

                state = Updater._read_update_state()
                self.assertTrue(state.get("existing_flag"))
                self.assertEqual(state.get("postponed_tag"), "v1.2.0")
                self.assertGreater(state.get("postponed_until", 0), 0)

    def test_concurrent_update_state_thread_safety(self):
        """Múltiples hilos llamando a _update_state concurrentemente no pierden claves."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = Path(tmp_dir) / "update_state.json"
            with patch("core.updater.UPDATE_STATE_FILE", test_file):
                errors = []
                threads = []

                def worker(thread_id):
                    try:
                        for i in range(10):
                            Updater._update_state(**{f"th_{thread_id}_{i}": i})
                    except Exception as e:
                        errors.append(e)

                for tid in range(5):
                    t = threading.Thread(target=worker, args=(tid,))
                    threads.append(t)
                    t.start()

                for t in threads:
                    t.join(timeout=5)

                self.assertEqual(len(errors), 0, f"Errores concurrentes: {errors}")
                final_state = Updater._read_update_state()
                # 5 hilos x 10 escrituras = 50 claves registradas
                self.assertEqual(len(final_state), 50)


class TestSmartRadioMixFilteringPhase3(unittest.TestCase):
    """Test #2: Filtrado inteligente de Radio/Mixes autogenerados en extract_playlist_urls."""

    def test_youtube_watch_radio_mix_returns_empty_list(self):
        """URL con /watch?v=...&list=RD... debe devolver [] para descargar solo la pista individual."""
        urls_to_test = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=RDdQw4w9WgXcQ",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=RDdQw4w9WgXcQ&start_radio=1",
            "https://music.youtube.com/watch?v=dQw4w9WgXcQ&list=RDAMVMdQw4w9WgXcQ",
            "https://www.youtube.com/watch?v=xyz123&list=RDMMxyz123",
        ]
        for url in urls_to_test:
            result = DownloadEngine.extract_playlist_urls(url)
            self.assertEqual(result, [], f"Fallo al filtrar mix para URL: {url}")

    def test_real_playlists_and_albums_not_filtered(self):
        """Playlists reales (list=PL...) o albums (list=OLAK...) se extraen con yt_dlp."""
        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_instance = MagicMock()
            mock_ydl_class.return_value.__enter__.return_value = mock_instance
            mock_instance.extract_info.return_value = {
                "entries": [
                    {"id": "vid1", "url": "https://www.youtube.com/watch?v=vid1"},
                    {"id": "vid2", "url": "https://www.youtube.com/watch?v=vid2"},
                ]
            }

            # 1. Playlist tradicional con list=PL...
            res_pl = DownloadEngine.extract_playlist_urls(
                "https://www.youtube.com/watch?v=vid1&list=PLMC9KNkIncKtPzgY-5rmhvj7fax8fdxoj"
            )
            self.assertEqual(len(res_pl), 2)

            # 2. Album YouTube Music con list=OLAK...
            res_album = DownloadEngine.extract_playlist_urls(
                "https://www.youtube.com/watch?v=vid1&list=OLAK5uy_k123456789"
            )
            self.assertEqual(len(res_album), 2)

    def test_dedicated_playlist_page_with_rd_not_filtered(self):
        """Una ruta dedicada /playlist con list=RDtest no debe filtrarse como /watch."""
        with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
            mock_instance = MagicMock()
            mock_ydl_class.return_value.__enter__.return_value = mock_instance
            mock_instance.extract_info.return_value = {
                "entries": [{"id": "item1", "url": "https://www.youtube.com/watch?v=item1"}]
            }
            res = DownloadEngine.extract_playlist_urls("https://www.youtube.com/playlist?list=RDtest")
            self.assertEqual(len(res), 1)


class TestAnsiDeduplicationPhase3(unittest.TestCase):
    """Test #3: Deduplicación de expresiones regulares ANSI en todos los módulos."""

    def test_ansi_regex_identity_and_functions(self):
        # Módulo downloader es la única fuente de verdad
        self.assertIs(console_view_mod._ANSI_RE, ANSI_ESCAPE_RE)
        self.assertIs(progress_bar_mod._ANSI_RE, ANSI_ESCAPE_RE)
        self.assertIs(app_window_mod.ANSI_ESCAPE_RE, ANSI_ESCAPE_RE)

        # Funciones clean_ansi / _clean_text
        self.assertIs(progress_bar_mod._clean_text, clean_ansi)
        self.assertIs(app_window_mod._clean_text, clean_ansi)


class TestCustomDestinationAndAppWindowPhase3(unittest.TestCase):
    """Test #4: Selector de carpeta personalizada y atributos de clase en AppWindow."""

    def setUp(self):
        with patch.object(AppWindow, "__init__", lambda s: None):
            self.app = AppWindow()
            self.app.download_queue = queue.Queue()
            self.app.is_downloading = False
            self.app._queue_total_items = 0
            self.app._queue_completed_items = 0
            self.app._custom_destination = None
            self.app.download_card = MagicMock()
            self.app.destination_label = MagicMock()
            self.app.downloader = MagicMock()
            self.app.after = MagicMock(side_effect=lambda d, fn: fn() if callable(fn) else None)

    def test_class_level_defaults_preserved(self):
        """Verifica que los atributos a nivel de clase existen con sus valores esperados."""
        self.assertEqual(AppWindow._queue_total_items, 0)
        self.assertEqual(AppWindow._queue_completed_items, 0)
        self.assertIsNone(AppWindow._custom_destination)

    def test_get_current_destination_default_behavior(self):
        """Sin carpeta personalizada, retorna MUSIC_DIR para MP3 y VIDEO_DIR para MP4."""
        self.app.download_card.get_format.return_value = "MP3 (audio)"
        self.assertEqual(self.app._get_current_destination(), MUSIC_DIR)

        self.app.download_card.get_format.return_value = "MP4 (video)"
        self.assertEqual(self.app._get_current_destination(), VIDEO_DIR)

    def test_get_current_destination_custom_override(self):
        """Con _custom_destination configurado, se ignora el formato y se retorna la ruta personalizada."""
        custom_path = Path("C:/MiCarpetaPersonalizada")
        self.app._custom_destination = custom_path

        self.app.download_card.get_format.return_value = "MP3 (audio)"
        self.assertEqual(self.app._get_current_destination(), custom_path)

        self.app.download_card.get_format.return_value = "MP4 (video)"
        self.assertEqual(self.app._get_current_destination(), custom_path)

    @patch("customtkinter.filedialog.askdirectory")
    def test_choose_custom_folder_sets_destination_and_updates_label(self, mock_askdirectory):
        mock_askdirectory.return_value = "D:/MusicaEspecial"

        self.app._choose_custom_folder()

        self.assertEqual(self.app._custom_destination, Path("D:/MusicaEspecial"))
        self.app.destination_label.configure.assert_called_with(text="Destino: MusicaEspecial")

    @patch("customtkinter.filedialog.askdirectory")
    def test_choose_custom_folder_cancelled_keeps_previous(self, mock_askdirectory):
        mock_askdirectory.return_value = ""  # Usuario canceló el diálogo

        self.app._custom_destination = None
        self.app._choose_custom_folder()
        self.assertIsNone(self.app._custom_destination)
        self.app.destination_label.configure.assert_not_called()

    def test_run_download_thread_calls_execute_download_directly(self):
        """Verifica que _run_download_thread invoque execute_download directamente."""
        dest = Path("C:/Dest")
        self.app.downloader.execute_download.return_value = None

        with patch.object(self.app, "_on_single_download_success") as mock_success:
            self.app._run_download_thread(
                url="https://youtube.com/watch?v=123",
                fmt="MP3",
                quality="320 kbps",
                destination=dest,
                embed_thumbnail=True,
            )
            self.app.downloader.execute_download.assert_called_once_with(
                url="https://youtube.com/watch?v=123",
                format_type="MP3",
                quality="320 kbps",
                destination_dir=dest,
                embed_thumbnail=True,
            )
            mock_success.assert_called_once_with(embed_thumbnail=True)


class TestDocumentationAndCIPhase3(unittest.TestCase):
    """Test #5: Verificación de consistencia de versión v1.1.0 y suite en GitHub Actions."""

    def test_readme_version_references(self):
        readme_path = Path(__file__).resolve().parent.parent / "README.md"
        content = readme_path.read_text(encoding="utf-8")

        self.assertIn("v1.1.0", content)
        self.assertNotIn("v1.0.9", content)
        self.assertNotIn("v1.0.7", content)

    def test_github_workflow_includes_tests_step(self):
        wf_path = Path(__file__).resolve().parent.parent / ".github" / "workflows" / "build-release.yml"
        content = wf_path.read_text(encoding="utf-8")

        self.assertIn("Run unit tests", content)
        self.assertIn("python -m unittest discover -s tests -v", content)
        # Asegurar que está ubicado antes del paso de pyinstaller / Build executable
        tests_idx = content.find("Run unit tests")
        build_idx = content.find("Build executable")
        self.assertTrue(0 < tests_idx < build_idx)


if __name__ == "__main__":
    unittest.main()
