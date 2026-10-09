import os
import sys
from pathlib import Path

# Versión y metadatos del software
APP_NAME = "Youtify"
APP_VERSION = "1.0.9"
APP_AUTHOR = "jonathanZM15"

# Resolución de directorios de ejecución (Portable / Instalado / Desarrollo)
def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent

BASE_DIR = get_base_dir()

# Rutas estándar del sistema
LOCAL_APPDATA = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
USER_DOWNLOADS = Path.home() / "Downloads" / APP_NAME

# Carpetas de destino
MUSIC_DIR = USER_DOWNLOADS / "Musica_Descargada"
VIDEO_DIR = USER_DOWNLOADS / "descargas_videos"
APPDATA_FFMPEG_DIR = LOCAL_APPDATA / APP_NAME / "ffmpeg"
BUNDLED_FFMPEG_DIR = BASE_DIR / "ffmpeg"
ICON_PATH = BASE_DIR / "icon.ico"

# Límites y optimizaciones de hardware / memoria
MAX_LOG_BUFFER_LINES = 200
PROGRESS_THROTTLE_SEC = 0.35
DOWNLOAD_TIMEOUT_SEC = 30
FFMPEG_DOWNLOAD_TIMEOUT_SEC = 120
HTTP_CHUNK_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB chunks
BUFFER_SIZE_BYTES = 64 * 1024             # 64 KB read buffer
CONCURRENT_FRAGMENT_DOWNLOADS = 4

# Fuentes remotas de componentes seguros
FFMPEG_OFFICIAL_URL = (
    "https://github.com/BtbN/FFmpeg-Builds/releases/download/"
    "latest/ffmpeg-master-latest-win64-gpl.zip"
)

# Integración con GitHub Releases (Actualizaciones automáticas)
GITHUB_REPO = "jonathanZM15/YOUTIFY-MUSICA-VIDEO"
GITHUB_API_LATEST_RELEASE = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
GITHUB_RELEASES_URL = f"https://github.com/{GITHUB_REPO}/releases"
UPDATE_STATE_FILE = LOCAL_APPDATA / APP_NAME / "update_state.json"

# Dominios autorizados de YouTube (seguridad cibernética / anti-phishing / anti-injection)
VALID_YOUTUBE_HOSTS = frozenset({
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
})

# Configuración de extracción antibot de YouTube: emulación de clientes móviles oficiales (iOS / Android / Web)
# Elimina la necesidad de Node.js o runtimes externos en la máquina del usuario final.
DEFAULT_YOUTUBE_EXTRACTOR_ARGS = {
    "youtube": {
        "player_client": ["ios", "android", "web"],
    }
}


# Opciones disponibles en la interfaz
VIDEO_QUALITIES = ["Máxima", "1080p", "720p", "480p", "360p"]
AUDIO_QUALITIES = ["Máxima", "320 kbps", "256 kbps", "192 kbps", "128 kbps"]

# Mapa de resoluciones de video (altura en px)
QUALITY_MAP = {
    "1080p": 1080,
    "720p": 720,
    "480p": 480,
    "360p": 360,
}

# Mapa de calidad de compresión de audio para FFmpegExtractAudio
# "0" = VBR de máxima calidad / menor compresión acústica; "320"/"256"/etc = CBR en kbps
AUDIO_QUALITY_MAP = {
    "Máxima": "0",
    "320 kbps": "320",
    "256 kbps": "256",
    "192 kbps": "192",
    "128 kbps": "128",
}

# Límites de optimización de carátula / thumbnail (evita sobrepeso en MP3/MP4)
THUMBNAIL_MAX_DIMENSION = 600      # Redimensión máxima de 600x600 px manteniendo proporción
THUMBNAIL_JPEG_QUALITY = 85        # Calidad de compresión JPEG (~30-60 KB vs 2-5 MB en PNG)
DEFAULT_EMBED_THUMBNAIL = True

