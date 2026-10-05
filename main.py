import multiprocessing
import sys
from pathlib import Path

# Fix fundamental para PyInstaller en Windows con subprocesos y multiprocessing
multiprocessing.freeze_support()

# Garantizar que la raíz del proyecto esté en el sys.path tanto en dev como compilado
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import customtkinter as ctk
from ui import AppWindow


def main() -> None:
    """Inicia la aplicación de escritorio Youtify."""
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    app = AppWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
