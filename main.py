import multiprocessing
import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Fix fundamental para PyInstaller en Windows con subprocesos y multiprocessing
multiprocessing.freeze_support()

# Garantizar que la raíz del proyecto esté en el sys.path tanto en dev como compilado
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def main() -> None:
    """Inicia la aplicación de escritorio Youtify."""
    if "--self-check" in sys.argv:
        import json
        import importlib.util
        from core.runtime import javascript_options
        from config.settings import APP_VERSION, BUNDLED_FFMPEG_DIR, ICON_PATH
        result = dict(version=APP_VERSION, frozen=bool(getattr(sys, "frozen", False)),
            ffmpeg=(BUNDLED_FFMPEG_DIR / "ffmpeg.exe").is_file(),
            ffprobe=(BUNDLED_FFMPEG_DIR / "ffprobe.exe").is_file(),
            javascript=bool(javascript_options()["js_runtimes"]),
            ejs=importlib.util.find_spec("yt_dlp_ejs") is not None, icon=ICON_PATH.is_file())
        destination = Path(sys.argv[sys.argv.index("--self-check") + 1])
        destination.write_text(json.dumps(result, indent=2), encoding="utf-8")
        return
    instance = None
    if sys.platform == "win32":
        from core.single_instance import SingleInstance
        instance = SingleInstance()
        if not instance.acquire():
            instance.close()
            return
    try:
        from core.managed_updates import ManagedUpdates
        if ManagedUpdates().redirect(release_lock=instance.close if instance else None):
            return
        if instance and not instance.acquire():
            return
        _run_app(instance)
    finally:
        if instance:
            instance.close()


def _run_app(instance):
    # Acquire the lock before importing Tk, yt-dlp and the rest of the GUI.
    import customtkinter as ctk
    from ui import AppWindow
    from config.settings import LOG_FILE
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, handlers=[RotatingFileHandler(
        LOG_FILE, maxBytes=2_000_000, backupCount=3, encoding="utf-8")],
        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")

    app = AppWindow()
    if instance:
        instance.attach(app)
    app.mainloop()


if __name__ == "__main__":
    main()
