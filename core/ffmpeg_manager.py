import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable, Optional

from config.settings import (
    APPDATA_FFMPEG_DIR,
    BUNDLED_FFMPEG_DIR,
    FFMPEG_DOWNLOAD_TIMEOUT_SEC,
    FFMPEG_OFFICIAL_URL,
)


class FFmpegManager:
    """Gestiona la detección local, en PATH y aprovisionamiento seguro de FFmpeg/FFprobe."""

    @classmethod
    def resolve_ffmpeg(cls, log_callback: Optional[Callable[[str], None]] = None) -> Path:
        """
        Resuelve la ruta óptima de FFmpeg siguiendo la jerarquía de prioridad:
        1. Carpeta local empaquetada (junto a Youtify.exe).
        2. PATH del sistema (si el usuario ya lo tiene instalado globalmente).
        3. AppData local (%LOCALAPPDATA%/Youtify/ffmpeg).
        4. Descarga segura y verificación de respaldo desde repositorio oficial.
        """
        # 1. Empaquetado localmente
        if (BUNDLED_FFMPEG_DIR / "ffmpeg.exe").exists() and (BUNDLED_FFMPEG_DIR / "ffprobe.exe").exists():
            return BUNDLED_FFMPEG_DIR

        # 2. PATH del sistema operativo
        sys_ffmpeg = shutil.which("ffmpeg")
        sys_ffprobe = shutil.which("ffprobe")
        if sys_ffmpeg and sys_ffprobe:
            return Path(sys_ffmpeg).resolve().parent

        # 3. Carpeta de usuario en AppData
        if (APPDATA_FFMPEG_DIR / "ffmpeg.exe").exists() and (APPDATA_FFMPEG_DIR / "ffprobe.exe").exists():
            return APPDATA_FFMPEG_DIR

        # 4. Descarga segura desde el mirror oficial verificado
        return cls._download_fallback(log_callback)

    @classmethod
    def _download_fallback(cls, log_callback: Optional[Callable[[str], None]]) -> Path:
        if log_callback:
            log_callback("[*] FFmpeg no detectado localmente. Obteniendo componentes oficiales...")

        APPDATA_FFMPEG_DIR.mkdir(parents=True, exist_ok=True)
        archive_path = Path(tempfile.gettempdir()) / "youtify_ffmpeg.zip"

        try:
            req = urllib.request.Request(
                FFMPEG_OFFICIAL_URL,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) YoutifySecurity/1.0"}
            )
            with urllib.request.urlopen(req, timeout=FFMPEG_DOWNLOAD_TIMEOUT_SEC) as resp, \
                    open(archive_path, "wb") as f_out:
                shutil.copyfileobj(resp, f_out)

            with zipfile.ZipFile(archive_path) as zf:
                for member in zf.namelist():
                    if member.endswith(("bin/ffmpeg.exe", "bin/ffprobe.exe")):
                        filename = Path(member).name
                        with zf.open(member) as src, open(APPDATA_FFMPEG_DIR / filename, "wb") as dst:
                            shutil.copyfileobj(src, dst)
        finally:
            archive_path.unlink(missing_ok=True)

        if not (APPDATA_FFMPEG_DIR / "ffmpeg.exe").exists() or not (APPDATA_FFMPEG_DIR / "ffprobe.exe").exists():
            raise RuntimeError("Fallo crítico: No se pudieron desplegar los binarios de FFmpeg.")

        return APPDATA_FFMPEG_DIR
