import gc
import shutil
import time
from pathlib import Path
from typing import Callable, Optional

from config.settings import (
    BUFFER_SIZE_BYTES,
    CONCURRENT_FRAGMENT_DOWNLOADS,
    DOWNLOAD_TIMEOUT_SEC,
    HTTP_CHUNK_SIZE_BYTES,
    PROGRESS_THROTTLE_SEC,
    QUALITY_MAP,
)
from core.ffmpeg_manager import FFmpegManager


class DownloadEngine:
    """Motor de descarga y conversión multi-hilo con optimizaciones de hardware, RAM y metadatos ID3."""

    def __init__(
        self,
        on_progress: Optional[Callable[[float, str, str, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None,
        on_status: Optional[Callable[[str, str], None]] = None,
    ):
        self.on_progress = on_progress
        self.on_log = on_log
        self.on_status = on_status
        self._last_progress_time = 0.0

    @staticmethod
    def extract_metadata_fast(url: str) -> Optional[dict]:
        """Extrae metadatos y miniatura de forma ultrarrápida sin descargar el archivo."""
        from yt_dlp import YoutubeDL
        opts = {
            "extract_flat": False,
            "skip_download": True,
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 8,
        }
        try:
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    return None
                # Si es una playlist, obtener el primer video o datos generales
                entries = info.get("entries")
                if entries:
                    first = list(entries)[0] if isinstance(entries, (list, tuple)) else next(iter(entries), None)
                    return {
                        "title": info.get("title") or (first.get("title") if first else "Playlist"),
                        "channel": info.get("uploader") or info.get("channel") or (first.get("uploader") if first else "Desconocido"),
                        "duration": info.get("playlist_count", 0),
                        "thumbnail": info.get("thumbnail") or (first.get("thumbnail") if first else None),
                        "is_playlist": True,
                    }

                duration_secs = info.get("duration") or 0
                minutes = int(duration_secs // 60)
                seconds = int(duration_secs % 60)
                dur_str = f"{minutes}:{seconds:02d}"

                return {
                    "title": info.get("title", "Video de YouTube"),
                    "channel": info.get("uploader") or info.get("channel") or "Desconocido",
                    "duration": dur_str,
                    "thumbnail": info.get("thumbnail"),
                    "is_playlist": False,
                }
        except Exception:
            return None

    def execute_download(
        self,
        url: str,
        format_type: str,
        quality: str,
        destination_dir: Path,
    ) -> None:
        destination_dir.mkdir(parents=True, exist_ok=True)
        is_audio = format_type.startswith("MP3")

        self._log(f"[+] Carpeta destino: {destination_dir.name}")
        ffmpeg_dir = FFmpegManager.resolve_ffmpeg(log_callback=self._log)

        options = self._build_yt_dlp_options(
            is_audio=is_audio,
            destination=destination_dir,
            ffmpeg_dir=ffmpeg_dir,
            quality=quality,
        )

        self._log("[+] Conectando con los servidores de YouTube...")
        if self.on_status:
            self.on_status("connecting", "Conectando con servidores...")

        from yt_dlp import YoutubeDL
        try:
            with YoutubeDL(options) as downloader:
                downloader.download([url])
        finally:
            gc.collect()

    def _progress_hook(self, data: dict) -> None:
        status = data.get("status")
        if status == "downloading":
            now = time.monotonic()
            if now - self._last_progress_time < PROGRESS_THROTTLE_SEC:
                return
            self._last_progress_time = now

            pct_str = data.get("_percent_str", "0%").strip()
            speed_str = data.get("_speed_str", "—").strip()
            eta_str = data.get("_eta_str", "").strip()

            msg = f"⚡ Descargando: {pct_str} a {speed_str}"
            if eta_str:
                msg += f" (restante: {eta_str})"
            self._log(msg)

            try:
                numeric_progress = float(pct_str.replace("%", "").replace(",", ".").strip()) / 100.0
                numeric_progress = max(0.0, min(1.0, numeric_progress))
            except ValueError:
                numeric_progress = 0.0

            if self.on_progress:
                self.on_progress(numeric_progress, pct_str, speed_str, eta_str)

        elif status == "finished":
            self._log("[*] Conversión y etiquetado ID3 de metadatos con FFmpeg...")
            if self.on_status:
                self.on_status("converting", "Incrustando portada y metadatos...")

    def _build_yt_dlp_options(
        self,
        is_audio: bool,
        destination: Path,
        ffmpeg_dir: Path,
        quality: Optional[str] = None,
    ) -> dict:
        options = {
            "outtmpl": str(destination / "%(title)s.%(ext)s"),
            "windowsfilenames": True,
            "restrictfilenames": True,
            "noplaylist": False,
            "retries": 10,
            "fragment_retries": 10,
            "socket_timeout": DOWNLOAD_TIMEOUT_SEC,
            "concurrent_fragment_downloads": CONCURRENT_FRAGMENT_DOWNLOADS,
            "buffersize": BUFFER_SIZE_BYTES,
            "http_chunk_size": HTTP_CHUNK_SIZE_BYTES,
            "http_headers": {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/131.0 Safari/537.36"
                )
            },
            "progress_hooks": [self._progress_hook],
            "ffmpeg_location": str(ffmpeg_dir),
            "quiet": True,
            "no_warnings": True,
            "noprogress": False,
            # Inyección de metadatos ID3 completos
            "writethumbnail": True,
        }

        if shutil.which("node"):
            options["js_runtimes"] = {"node": {}}
            options["remote_components"] = {"ejs": ["github"]}

        if is_audio:
            options.update({
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "0",
                    },
                    {
                        # Inyectar tags ID3 (artista, álbum, título, fecha)
                        "key": "FFmpegMetadata",
                        "add_metadata": True,
                    },
                    {
                        # Incrustar portada oficial directamente en el MP3
                        "key": "EmbedThumbnail",
                    },
                ],
            })
        else:
            height = QUALITY_MAP.get(quality)
            selector = (
                f"bestvideo[height<={height}]+bestaudio/best[height<={height}]"
                if height else "bestvideo+bestaudio/best"
            )
            options.update({
                "format": selector,
                "merge_output_format": "mp4",
                "postprocessors": [
                    {
                        "key": "FFmpegMetadata",
                        "add_metadata": True,
                    },
                ],
            })

        return options

    def _log(self, message: str) -> None:
        if self.on_log:
            self.on_log(message)
