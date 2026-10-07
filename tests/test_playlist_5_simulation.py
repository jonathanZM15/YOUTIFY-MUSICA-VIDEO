import unittest
from unittest.mock import patch, MagicMock, call
import queue
from pathlib import Path

from ui.app_window import AppWindow


class TestPlaylist5Simulation(unittest.TestCase):
    def test_5_item_queue_execution_flow(self):
        """
        Simula una cola de 5 videos:
        - Video 1: Éxito normal (inicio inmediato sin pausa)
        - Video 2: 403 en intento 1 -> reintento exitoso en intento 2
        - Video 3: 403 permanente en ambos intentos -> modal de error -> continúa cola
        - Video 4: Éxito normal
        - Video 5: Éxito normal
        """
        with patch.object(AppWindow, "__init__", lambda s: None):
            app = AppWindow()
            app.download_queue = queue.Queue()
            app.is_downloading = False
            app._queue_total_items = 0
            app._queue_completed_items = 0
            app.downloader = MagicMock()
            app.console_view = MagicMock()
            app.progress_widget = MagicMock()
            app.download_btn = MagicMock()
            app.enqueue_btn = MagicMock()
            app.winfo_exists = MagicMock(return_value=True)

            delays_recorded = []
            def fake_after(delay_ms, fn=None):
                if fn:
                    delays_recorded.append((delay_ms, fn))
                return "timer_id"

            app.after = MagicMock(side_effect=fake_after)
            app._show_download_error = MagicMock()

            # Encolar 5 videos
            dest = Path("C:/Downloads")
            for i in range(1, 6):
                app.download_queue.put((f"https://youtube.com/watch?v={i}", "MP3", "320 kbps", dest))

            # Mapeo de comportamiento de descarga por URL
            attempts_per_url = {}

            def fake_execute(url, format_type, quality, destination_dir):
                attempts_per_url[url] = attempts_per_url.get(url, 0) + 1
                att = attempts_per_url[url]

                if url == "https://youtube.com/watch?v=1":
                    return  # Éxito inmediato
                elif url == "https://youtube.com/watch?v=2":
                    if att == 1:
                        raise Exception("HTTP Error 403: Forbidden")
                    return  # Éxito en reintento
                elif url == "https://youtube.com/watch?v=3":
                    raise Exception("HTTP Error 403: Forbidden")  # Falla ambos intentos
                elif url in ("https://youtube.com/watch?v=4", "https://youtube.com/watch?v=5"):
                    return  # Éxito

            app.downloader.execute_download.side_effect = fake_execute

            # Disparar inicio de la cola (primer video, sin delay)
            with patch("threading.Thread") as mock_thread, patch("time.sleep") as mock_sleep:
                # 1. Video 1:
                app._process_next_in_queue(apply_delay=False)
                # Video 1 arrancó sin delay previo
                thread_target = mock_thread.call_args[1]["target"]
                thread_args = mock_thread.call_args[1]["args"]
                # Ejecutar worker de Video 1
                thread_target(*thread_args)

                # Verificar que completó y llamó a _on_single_download_success
                # En fake_after se habrá programado _on_single_download_success
                self.assertTrue(any(fn == app._on_single_download_success for _, fn in delays_recorded))

                # Ejecutar _on_single_download_success
                delays_recorded.clear()
                app._on_single_download_success()

                # Debe haber programado pausa antibot para Video 2 (1.5s - 4s)
                self.assertEqual(len(delays_recorded), 1)
                delay_ms, resume_fn = delays_recorded.pop(0)
                self.assertTrue(1500 <= delay_ms <= 4000, f"Delay {delay_ms} fuera de rango")

                # 2. Despertar timer y procesar Video 2:
                mock_thread.reset_mock()
                resume_fn()
                thread_target = mock_thread.call_args[1]["target"]
                thread_args = mock_thread.call_args[1]["args"]
                
                # Ejecutar worker de Video 2 (tendrá 403 en intento 1 y éxito en intento 2)
                thread_target(*thread_args)
                # Debe haber dormido entre 5s y 8s por el reintento de 403
                mock_sleep.assert_called_once()
                self.assertTrue(5.0 <= mock_sleep.call_args[0][0] <= 8.0)
                self.assertEqual(attempts_per_url["https://youtube.com/watch?v=2"], 2)

                # Video 2 tuvo éxito tras el reintento:
                delays_recorded.clear()
                app._on_single_download_success()

                # Debe haber programado pausa antibot para Video 3
                delay_ms, resume_fn = delays_recorded.pop(0)
                self.assertTrue(1500 <= delay_ms <= 4000)

                # 3. Despertar timer y procesar Video 3 (Falla definitiva con 403):
                mock_thread.reset_mock()
                mock_sleep.reset_mock()
                resume_fn()
                thread_target = mock_thread.call_args[1]["target"]
                thread_args = mock_thread.call_args[1]["args"]

                thread_target(*thread_args)
                # Video 3 intentó 2 veces y falló
                self.assertEqual(attempts_per_url["https://youtube.com/watch?v=3"], 2)
                mock_sleep.assert_called_once()  # Durmió antes del reintento

                # Comprobamos que programó el modal de error y la continuación de la cola
                callbacks_scheduled = [fn for _, fn in delays_recorded]
                delays_recorded.clear()
                # Ejecutar los callbacks programados para Video 3
                for cb in callbacks_scheduled:
                    cb()

                # Debe haber mostrado el modal de error con Node.js recomendado
                app._show_download_error.assert_called_once()
                error_shown = app._show_download_error.call_args[0][0]
                self.assertIn("Node.js LTS", error_shown)

                # 4. Y la cola continuó! Debe haberse programado la pausa antibot para Video 4:
                # Comprobamos si hay pausa para video 4
                self.assertTrue(len(delays_recorded) >= 1)
                delay_ms, resume_fn = delays_recorded.pop(0)
                self.assertTrue(1500 <= delay_ms <= 4000)

                # Despertar timer y procesar Video 4:
                mock_thread.reset_mock()
                resume_fn()
                thread_target = mock_thread.call_args[1]["target"]
                thread_args = mock_thread.call_args[1]["args"]
                thread_target(*thread_args)
                self.assertEqual(attempts_per_url["https://youtube.com/watch?v=4"], 1)

                # Video 4 éxito
                delays_recorded.clear()
                app._on_single_download_success()

                # Pausa para Video 5
                delay_ms, resume_fn = delays_recorded.pop(0)
                self.assertTrue(1500 <= delay_ms <= 4000)

                # 5. Despertar timer y procesar Video 5:
                mock_thread.reset_mock()
                resume_fn()
                thread_target = mock_thread.call_args[1]["target"]
                thread_args = mock_thread.call_args[1]["args"]
                thread_target(*thread_args)
                self.assertEqual(attempts_per_url["https://youtube.com/watch?v=5"], 1)

                # Video 5 éxito
                delays_recorded.clear()
                app._on_single_download_success()

                # Cola vacía: NO debe haber más pausas, debe finalizar
                self.assertTrue(app.download_queue.empty())
                self.assertFalse(app.is_downloading)
                app.progress_widget.set_completed.assert_called_once()

                # Verificar que en todo momento activo el badge solo recibió (current, total)
                active_calls = app.progress_widget.set_active_download.call_args_list
                self.assertTrue(len(active_calls) >= 5)
                for call_args in active_calls:
                    cur, tot = call_args[0]
                    self.assertEqual(tot, 5)
                    self.assertTrue(1 <= cur <= 5)


if __name__ == "__main__":
    unittest.main()
