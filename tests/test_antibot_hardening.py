import unittest
from unittest.mock import patch, MagicMock
import queue
import time
from pathlib import Path

from ui.app_window import AppWindow
from core.updater import Updater
from core.downloader import DownloadEngine


class TestAntibotHardening(unittest.TestCase):
    def setUp(self):
        # Evitar crear la ventana gráfica real en tests headless
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
            self.app.after = MagicMock()
            self.app.winfo_exists = MagicMock(return_value=True)

    def test_nodejs_detection_found(self):
        with patch("shutil.which", return_value="C:\\Program Files\\nodejs\\node.EXE"):
            AppWindow._check_nodejs_environment(self.app)
            self.app.console_view.append_log.assert_called_with(
                "[✓] Entorno JavaScript: Node.js detectado para desafíos antibot."
            )

    def test_nodejs_detection_missing(self):
        with patch("shutil.which", return_value=None):
            AppWindow._check_nodejs_environment(self.app)
            args, _ = self.app.console_view.append_log.call_args
            self.assertIn("Node.js no detectado", args[0])
            self.assertIn("https://nodejs.org/", args[0])

    def test_queue_delay_first_item_no_delay(self):
        # Simular 2 elementos en cola
        dest = Path("C:/Downloads")
        self.app.download_queue.put(("https://youtube.com/watch?v=1", "MP3", "320 kbps", dest))
        self.app.download_queue.put(("https://youtube.com/watch?v=2", "MP3", "320 kbps", dest))

        with patch("threading.Thread") as mock_thread:
            # Primera descarga (apply_delay=False por defecto)
            self.app._process_next_in_queue(apply_delay=False)
            # Debe iniciar inmediatamente el hilo, sin programar after con delay
            mock_thread.assert_called_once()
            self.assertTrue(self.app.is_downloading)

    def test_queue_delay_subsequent_items(self):
        # Simular segundo elemento con apply_delay=True
        dest = Path("C:/Downloads")
        self.app.download_queue.put(("https://youtube.com/watch?v=2", "MP3", "320 kbps", dest))

        self.app._process_next_in_queue(apply_delay=True)

        # Debe llamar a self.after con un delay entre 1500 y 4000 ms
        self.app.after.assert_called_once()
        delay_ms, callback = self.app.after.call_args[0]
        self.assertTrue(1500 <= delay_ms <= 4000, f"Delay {delay_ms} fuera del rango 1500-4000ms")
        self.assertIn("Pausa antibot preventiva", self.app.console_view.append_log.call_args[0][0])

    def test_403_isolated_retry_succeeds(self):
        # Simular error 403 en intento 1 y éxito en intento 2
        dest = Path("C:/Downloads")
        call_count = 0

        def fake_download(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("HTTP Error 403: Forbidden")
            return

        self.app.downloader.execute_download.side_effect = fake_download

        with patch("time.sleep") as mock_sleep:
            self.app._run_download_thread(
                url="https://youtube.com/watch?v=1",
                fmt="MP3",
                quality="320 kbps",
                destination=dest,
            )

            # Debe haber dormido entre 5.0 y 8.0s
            mock_sleep.assert_called_once()
            sleep_duration = mock_sleep.call_args[0][0]
            self.assertTrue(5.0 <= sleep_duration <= 8.0, f"Sleep {sleep_duration} fuera de rango 5-8s")

            # Debe haber ejecutado 2 intentos
            self.assertEqual(call_count, 2)
            # Debe haber notificado éxito
            self.app.after.assert_called_with(0, self.app._on_single_download_success)

    def test_403_permanent_failure_continues_queue(self):
        # Simular error 403 persistente en ambos intentos
        dest = Path("C:/Downloads")
        self.app.downloader.execute_download.side_effect = Exception("HTTP Error 403: Forbidden")

        with patch("time.sleep") as mock_sleep, patch.object(self.app, "_show_download_error") as mock_show_error:
            self.app._run_download_thread(
                url="https://youtube.com/watch?v=1",
                fmt="MP3",
                quality="320 kbps",
                destination=dest,
            )

            # Debe haber dormido 1 vez antes del reintento
            mock_sleep.assert_called_once()
            # Debe haber llamado execute_download 2 veces
            self.assertEqual(self.app.downloader.execute_download.call_count, 2)

            # Debe haber llamado a _process_next_in_queue con delay para el siguiente elemento
            after_calls = [call[0] for call in self.app.after.call_args_list]
            # Verificar que alguna de las llamadas a after programa _process_next_in_queue
            scheduled_funcs = [call[1] for call in after_calls if len(call) >= 2]
            
            # Ejecutar las funciones programadas con after para verificar que continúa la cola
            processed_next = False
            with patch.object(self.app, "_process_next_in_queue") as mock_next_queue:
                for fn in scheduled_funcs:
                    if callable(fn):
                        fn()
                mock_next_queue.assert_called_with(apply_delay=True)

    def test_updater_yt_dlp_timestamp_logging(self):
        # Verificar que Updater registra y reporta fecha
        logs = []
        with patch("subprocess.run") as mock_sub:
            mock_sub.return_value = MagicMock(returncode=0, stdout="Requirement already satisfied")
            Updater.check_and_update_async(log_callback=logs.append)
            # Dar tiempo al hilo de Updater para ejecutar
            time.sleep(0.3)
            
            # Verificar logs generados
            joined_logs = "\n".join(logs)
            self.assertIn("yt-dlp", joined_logs)
            self.assertTrue(any("versión" in log or "actualización" in log for log in logs))


if __name__ == "__main__":
    unittest.main()
