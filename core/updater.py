import subprocess
import sys
import threading
from typing import Callable, Optional


class Updater:
    """Comprueba y actualiza silenciosamente yt-dlp en segundo plano para mitigar cambios en YouTube."""

    @classmethod
    def check_and_update_async(cls, log_callback: Optional[Callable[[str], None]] = None) -> None:
        def _task():
            try:
                # Comprobación segura con subprocess
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp", "--no-warn-script-location"],
                    capture_output=True,
                    text=True,
                    timeout=45,
                )
                if result.returncode == 0:
                    if "Requirement already satisfied" not in result.stdout and log_callback:
                        log_callback("[*] Componente de red yt-dlp actualizado automáticamente.")
            except Exception:
                # Silencioso para no degradar la experiencia de usuario si no hay conexión
                pass

        threading.Thread(target=_task, daemon=True).start()
