import subprocess
import sys
import threading
from typing import Callable, Optional


class Updater:
    """Comprueba de forma segura actualizaciones de red sin reejecutar el binario compilado."""

    @classmethod
    def check_and_update_async(cls, log_callback: Optional[Callable[[str], None]] = None) -> None:
        # En binarios compilados de PyInstaller (sys.frozen), sys.executable es Youtify.exe, no python.exe!
        # Si se ejecuta sys.executable -m pip en un .exe de PyInstaller, se abre Youtify infinitas veces.
        if getattr(sys, "frozen", False):
            # En modo .exe compilado, no llamar a pip via sys.executable
            return

        def _task():
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp", "--no-warn-script-location"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode == 0:
                    if "Requirement already satisfied" not in result.stdout and log_callback:
                        log_callback("[*] yt-dlp actualizado a la versión más reciente.")
            except Exception:
                pass

        threading.Thread(target=_task, daemon=True).start()
