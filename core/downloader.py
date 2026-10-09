import gc
import re
import shutil
import time
from pathlib import Path
from typing import Callable, Optional

# Regex estándar para suprimir secuencias de escape ANSI de terminal (colores, estilos, cursor)
ANSI_ESCAPE_RE = re.compile(
    r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])|\x1b\[[0-9;]*[a-zA-Z]|\x1b\[[0-9;]*m"
)


def clean_ansi(text: Optional[str]) -> str:
    """Elimina códigos de escape ANSI de secuencias de terminal (ej. colores de yt-dlp)."""
    if not text:
        return ""
    return ANSI_ESCAPE_RE.sub("", str(text)).strip()


from config.settings import (
    BUFFER_SIZE_BYTES,
    CONCURRENT_FRAGMENT_DOWNLOADS,
    DEFAULT_EMBED_THUMBNAIL,
    DEFAULT_YOUTUBE_EXTRACTOR_ARGS,
    DOWNLOAD_TIMEOUT_SEC,
    HTTP_CHUNK_SIZE_BYTES,
    PROGRESS_THROTTLE_SEC,
    QUALITY_MAP,
    AUDIO_QUALITY_MAP,
    THUMBNAIL_JPEG_QUALITY,
    THUMBNAIL_MAX_DIMENSION,
)
from core.ffmpeg_manager import FFmpegManager
from PIL import Image
from yt_dlp.postprocessor import PostProcessor

# NOTA DE ARQUITECTURA / ROADMAP ANTIBOT:
# 1. Estrategia activa (inmediata y predeterminada): Emulación en cascada de clientes oficiales
#    móviles (player_client: ios, android, web). Resuelve el error "Sign in to confirm you're not a bot"
#    sin requerir Node.js, cookies de navegador ni herramientas de programador en la máquina del usuario.
# 2. Roadmap mediano plazo: Integración de un motor JS ultra-ligero embebido (como QuickJS portátil ~2MB)
#    directamente en el empaquetador del instalador (.iss / dist) como salvaguarda autónoma si YouTube
#    bloquea en el futuro clientes móviles.


def optimize_thumbnail(
    thumb_path: Path,
    max_dimension: int = THUMBNAIL_MAX_DIMENSION,
    quality: int = THUMBNAIL_JPEG_QUALITY,
) -> Path:
    """
    Optimiza la imagen de carátula descargada con Pillow:
    - Si ya es JPEG y sus dimensiones están dentro del límite, no reprocesa innecesariamente.
    - Si supera max_dimension, redimensiona manteniendo relación de aspecto.
    - Convierte a JPEG con compresión calidad 80-85 (~30-60 KB vs 2-5 MB en PNG/WebP).
    """
    if not thumb_path or not thumb_path.exists():
        return thumb_path

    try:
        with Image.open(thumb_path) as img:
            width, height = img.size
            img_format = (img.format or "").upper()

            # Evitar reprocesar si ya es un JPEG dentro de los límites
            if img_format == "JPEG" and width <= max_dimension and height <= max_dimension:
                return thumb_path

            # Redimensionar solo si excede las dimensiones máximas
            if width > max_dimension or height > max_dimension:
                img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

            # Normalizar modos de color (RGBA, LA, P) a RGB con fondo blanco
            if img.mode in ("RGBA", "LA", "P"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                mask = img.split()[-1] if "A" in img.mode else None
                background.paste(img, mask=mask)
                final_img = background
            elif img.mode != "RGB":
                final_img = img.convert("RGB")
            else:
                final_img = img

            target_path = thumb_path.with_suffix(".jpg")
            final_img.save(
                target_path,
                format="JPEG",
                quality=quality,
                optimize=True,
            )

        # Eliminar archivo original si tenía extensión diferente (.webp, .png)
        if target_path.resolve() != thumb_path.resolve() and thumb_path.exists():
            thumb_path.unlink(missing_ok=True)

        return target_path
    except Exception:
        # En caso de cualquier error en la imagen, retornar la original para no romper la descarga
        return thumb_path


class ThumbnailOptimizerPP(PostProcessor):
    """Postprocesador que intercepta la miniatura descargada y la optimiza con Pillow antes de incrustarla."""

    def __init__(
        self,
        downloader=None,
        max_dimension: int = THUMBNAIL_MAX_DIMENSION,
        quality: int = THUMBNAIL_JPEG_QUALITY,
    ):
        super().__init__(downloader)
        self.max_dimension = max_dimension
        self.quality = quality

    def run(self, info: dict):
        thumbnails = info.get("thumbnails") or []
        for thumb in thumbnails:
            filepath = thumb.get("filepath")
            if filepath and Path(filepath).exists():
                optimized_path = optimize_thumbnail(
                    Path(filepath),
                    max_dimension=self.max_dimension,
                    quality=self.quality,
                )
                str_opt = str(optimized_path)
                thumb["filepath"] = str_opt
                if "__files_to_move" in info and filepath in info["__files_to_move"]:
                    info["__files_to_move"][str_opt] = info["__files_to_move"].pop(filepath)
        return [], info




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
        self._last_progress_value: float = 0.0
        self.is_audio: bool = False
        self._expected_stream_count: int = 1
        self._stream_phase_index: int = 0
        self._current_stream_id: Optional[str] = None
        self._phase_offset_bytes: int = 0
        self._phase_last_bytes: int = 0
        self._total_combined_bytes: int = 0

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
            "extractor_args": DEFAULT_YOUTUBE_EXTRACTOR_ARGS,
        }
        if shutil.which("node"):
            opts["js_runtimes"] = {"node": {}}
            opts["remote_components"] = {"ejs": ["github"]}
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

    @staticmethod
    def extract_playlist_urls(url: str) -> list[str]:
        """Detecta si la URL es una playlist/mix y extrae las URLs individuales de cada video de forma ultrarrápida."""
        if not url or ("list=" not in url and "playlist" not in url):
            return []

        from yt_dlp import YoutubeDL
        opts = {
            "extract_flat": "in_playlist",
            "skip_download": True,
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 8,
            "extractor_args": DEFAULT_YOUTUBE_EXTRACTOR_ARGS,
        }
        if shutil.which("node"):
            opts["js_runtimes"] = {"node": {}}
            opts["remote_components"] = {"ejs": ["github"]}
        try:
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    return []
                entries = info.get("entries")
                if not entries:
                    return []

                urls = []
                for entry in entries:
                    if not entry:
                        continue
                    video_url = entry.get("url")
                    video_id = entry.get("id")
                    if video_url and (video_url.startswith("http://") or video_url.startswith("https://")):
                        urls.append(video_url)
                    elif video_id:
                        urls.append(f"https://www.youtube.com/watch?v={video_id}")
                return urls
        except Exception:
            return []

    def execute_download(
        self,
        url: str,
        format_type: str,
        quality: str,
        destination_dir: Path,
        embed_thumbnail: bool = DEFAULT_EMBED_THUMBNAIL,
    ) -> None:
        destination_dir.mkdir(parents=True, exist_ok=True)
        is_audio = format_type.startswith("MP3")
        self.is_audio = is_audio
        self._last_progress_value = 0.0
        self._last_progress_time = 0.0
        self._stream_phase_index = 0
        self._current_stream_id = None
        self._phase_offset_bytes = 0
        self._phase_last_bytes = 0
        self._total_combined_bytes = 0
        self._expected_stream_count = 1 if is_audio else 2

        tag_calidad = f"MP3 Audio ({quality})" if is_audio else f"MP4 Video ({quality})"
        self._log(f"[+] Formato seleccionado: {tag_calidad}")
        self._log(f"[+] Carpeta destino: {destination_dir.name}")
        if embed_thumbnail:
            self._log("[+] Carátula: Incrustación y optimización activada (JPEG máx 600px)")
        else:
            self._log("[+] Carátula: Desactivada por el usuario (archivo ultraligero)")
        ffmpeg_dir = FFmpegManager.resolve_ffmpeg(log_callback=self._log)

        options = self._build_yt_dlp_options(
            is_audio=is_audio,
            destination=destination_dir,
            ffmpeg_dir=ffmpeg_dir,
            quality=quality,
            embed_thumbnail=embed_thumbnail,
        )

        from yt_dlp import YoutubeDL

        # Si es video (selector dual bestvideo+bestaudio), estimar el peso total combinado
        if not is_audio:
            try:
                meta_opts = {
                    "quiet": True,
                    "no_warnings": True,
                    "skip_download": True,
                    "format": options.get("format"),
                    "socket_timeout": 8,
                    "extractor_args": DEFAULT_YOUTUBE_EXTRACTOR_ARGS,
                }
                if shutil.which("node"):
                    meta_opts["js_runtimes"] = {"node": {}}
                    meta_opts["remote_components"] = {"ejs": ["github"]}
                with YoutubeDL(meta_opts) as ydl_meta:
                    meta_info = ydl_meta.extract_info(url, download=False)
                    if meta_info:
                        req_formats = meta_info.get("requested_formats")
                        if req_formats and len(req_formats) >= 2:
                            self._expected_stream_count = len(req_formats)
                            self._total_combined_bytes = sum(
                                f.get("filesize") or f.get("filesize_approx") or 0
                                for f in req_formats
                            )
                        else:
                            self._expected_stream_count = 1
                            self._total_combined_bytes = (
                                meta_info.get("filesize") or meta_info.get("filesize_approx") or 0
                            )
            except Exception:
                self._expected_stream_count = 2
                self._total_combined_bytes = 0

        self._log("[+] Conectando con los servidores de YouTube...")
        if self.on_status:
            self.on_status("connecting", "Conectando con servidores...")

        try:
            with YoutubeDL(options) as downloader:
                if embed_thumbnail:
                    embed_idx = next(
                        (i for i, pp in enumerate(downloader._pps.get("post_process", []))
                         if pp.__class__.__name__ == "EmbedThumbnailPP"),
                        None
                    )
                    optimizer = ThumbnailOptimizerPP(
                        downloader,
                        max_dimension=THUMBNAIL_MAX_DIMENSION,
                        quality=THUMBNAIL_JPEG_QUALITY,
                    )
                    if embed_idx is not None:
                        downloader._pps["post_process"].insert(embed_idx, optimizer)
                    else:
                        downloader._pps["post_process"].append(optimizer)

                downloader.download([url])
            # Limpieza de imágenes sueltas que yt-dlp pueda haber dejado
            for ext in ("*.webp", "*.jpg", "*.png", "*.jpeg"):
                for leftover in destination_dir.glob(ext):
                    try:
                        leftover.unlink(missing_ok=True)
                    except Exception:
                        pass
        finally:
            gc.collect()

    def _progress_hook(self, data: dict) -> None:
        status = data.get("status")
        if status == "downloading":
            now = time.monotonic()
            if now - self._last_progress_time < PROGRESS_THROTTLE_SEC:
                return
            self._last_progress_time = now

            # Detección de stream y cambio de fase (ej. de video a audio)
            stream_key = (data.get("info_dict") or {}).get("format_id") or data.get("filename")
            if self._current_stream_id is None:
                self._current_stream_id = stream_key
            elif stream_key and stream_key != self._current_stream_id:
                # Transición de stream detectada: acumular bytes de la fase previa
                self._phase_offset_bytes += self._phase_last_bytes
                self._phase_last_bytes = 0
                self._current_stream_id = stream_key
                self._stream_phase_index += 1

            # Extracción segura y robusta de bytes crudos con mitigación de None / tipos inesperados
            downloaded = data.get("downloaded_bytes")
            if downloaded is None or not isinstance(downloaded, (int, float)):
                downloaded = 0
            self._phase_last_bytes = downloaded

            stream_total = data.get("total_bytes")
            if stream_total is None or not isinstance(stream_total, (int, float)) or stream_total <= 0:
                stream_total = data.get("total_bytes_estimate")
                if stream_total is None or not isinstance(stream_total, (int, float)) or stream_total <= 0:
                    stream_total = 0

            frag_idx = data.get("fragment_index")
            frag_cnt = data.get("fragment_count")

            # Cálculo de progreso unificado y continuo
            if self.is_audio or self._expected_stream_count == 1:
                # Descarga de un solo stream (MP3 o video progresivo)
                if stream_total > 0 and downloaded > 0:
                    numeric_progress = max(0.0, min(1.0, float(downloaded) / float(stream_total)))
                    self._last_progress_value = numeric_progress
                elif (
                    isinstance(frag_idx, (int, float))
                    and isinstance(frag_cnt, (int, float))
                    and frag_cnt > 0
                ):
                    numeric_progress = max(0.0, min(1.0, float(frag_idx) / float(frag_cnt)))
                    self._last_progress_value = numeric_progress
                else:
                    numeric_progress = self._last_progress_value
            else:
                # Descarga combinada de dos streams (video + audio)
                if self._total_combined_bytes > 0:
                    # Progreso acumulativo exacto basado en el peso total de ambos streams
                    combined_bytes = self._phase_offset_bytes + downloaded
                    calc_prog = float(combined_bytes) / float(self._total_combined_bytes)
                    numeric_progress = max(self._last_progress_value, min(0.99, calc_prog))
                    self._last_progress_value = numeric_progress
                else:
                    # Fallback ponderado (Video = 0% a 90%, Audio = 90% a 99%)
                    if stream_total > 0 and downloaded > 0:
                        stream_frac = max(0.0, min(1.0, float(downloaded) / float(stream_total)))
                    elif (
                        isinstance(frag_idx, (int, float))
                        and isinstance(frag_cnt, (int, float))
                        and frag_cnt > 0
                    ):
                        stream_frac = max(0.0, min(1.0, float(frag_idx) / float(frag_cnt)))
                    else:
                        stream_frac = 0.0

                    if self._stream_phase_index == 0:
                        calc_prog = stream_frac * 0.90
                    else:
                        calc_prog = 0.90 + (stream_frac * 0.09)

                    numeric_progress = max(self._last_progress_value, min(0.99, calc_prog))
                    self._last_progress_value = numeric_progress

            # Formato de porcentaje textual coordinado con la barra
            if not self.is_audio and self._expected_stream_count > 1:
                pct_str = f"{numeric_progress * 100:.1f}%"
            else:
                raw_pct = data.get("_percent_str")
                if isinstance(raw_pct, str) and "N/A" not in raw_pct and raw_pct.strip():
                    pct_str = clean_ansi(raw_pct)
                elif numeric_progress > 0:
                    pct_str = f"{numeric_progress * 100:.1f}%"
                else:
                    pct_str = "0.0%"

            speed_str = clean_ansi(data.get("_speed_str")) or "—"
            eta_str = clean_ansi(data.get("_eta_str"))
            pct_str = clean_ansi(pct_str)

            msg = f"⚡ Descargando: {pct_str} a {speed_str}"
            if eta_str:
                msg += f" (restante: {eta_str})"
            self._log(msg)

            if self.on_progress:
                self.on_progress(numeric_progress, pct_str, speed_str, eta_str)

        elif status == "finished":
            if self.is_audio or self._expected_stream_count == 1:
                self._last_progress_value = 1.0
                self._log("[*] Conversión y etiquetado ID3 de metadatos con FFmpeg...")
                if self.on_status:
                    self.on_status("converting", "Incrustando portada y metadatos...")
                if self.on_progress:
                    self.on_progress(1.0, "100.0%", "—", "")
            else:
                # Video multi-stream: verificar qué stream acaba de finalizar
                if self._stream_phase_index == 0:
                    # Cerrar fase de video sin reiniciar barra visual
                    self._phase_offset_bytes += self._phase_last_bytes
                    self._phase_last_bytes = 0
                    self._stream_phase_index = 1
                    self._current_stream_id = None
                    self._log("[+] Stream de video completado. Descargando pista de audio...")
                    if self.on_progress:
                        pct_str = f"{self._last_progress_value * 100:.1f}%"
                        self.on_progress(self._last_progress_value, pct_str, "—", "")
                else:
                    # Finalizaron ambos streams
                    self._last_progress_value = 1.0
                    self._log("[*] Fusión de video y audio en MP4 con FFmpeg...")
                    if self.on_status:
                        self.on_status("converting", "Ensamblando pistas con FFmpeg...")
                    if self.on_progress:
                        self.on_progress(1.0, "100.0%", "—", "")

    def _build_yt_dlp_options(
        self,
        is_audio: bool,
        destination: Path,
        ffmpeg_dir: Path,
        quality: Optional[str] = None,
        embed_thumbnail: bool = DEFAULT_EMBED_THUMBNAIL,
    ) -> dict:
        options = {
            "outtmpl": str(destination / "%(title)s.%(ext)s"),
            "windowsfilenames": True,
            "restrictfilenames": True,
            "noplaylist": True,
            "retries": 10,
            "fragment_retries": 10,
            "socket_timeout": DOWNLOAD_TIMEOUT_SEC,
            "concurrent_fragment_downloads": CONCURRENT_FRAGMENT_DOWNLOADS,
            "buffersize": BUFFER_SIZE_BYTES,
            "http_chunk_size": HTTP_CHUNK_SIZE_BYTES,
            "color": "never",
            "http_headers": {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/131.0 Safari/537.36"
                )
            },
            "extractor_args": DEFAULT_YOUTUBE_EXTRACTOR_ARGS,
            "progress_hooks": [self._progress_hook],
            "ffmpeg_location": str(ffmpeg_dir),
            "quiet": True,
            "no_warnings": True,
            "noprogress": False,
        }

        if shutil.which("node"):
            options["js_runtimes"] = {"node": {}}
            options["remote_components"] = {"ejs": ["github"]}

        if is_audio:
            preferred_quality = AUDIO_QUALITY_MAP.get(quality, "0") if quality else "0"
            postprocessors = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": preferred_quality,
                },
                {
                    # Inyectar tags ID3 (artista, álbum, título, fecha)
                    "key": "FFmpegMetadata",
                    "add_metadata": True,
                },
            ]
            if embed_thumbnail:
                postprocessors.append({
                    # Incrustar portada oficial directamente en el MP3 y borrar la miniatura suelta
                    "key": "EmbedThumbnail",
                })

            options.update({
                "format": "bestaudio/best",
                "writethumbnail": embed_thumbnail,
                "postprocessors": postprocessors,
            })
        else:
            height = QUALITY_MAP.get(quality)
            selector = (
                f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/best"
                if height else "bestvideo+bestaudio/best/best"
            )
            postprocessors = [
                {
                    "key": "FFmpegMetadata",
                    "add_metadata": True,
                },
            ]
            if embed_thumbnail:
                postprocessors.append({
                    "key": "EmbedThumbnail",
                })

            options.update({
                "format": selector,
                "merge_output_format": "mp4",
                "writethumbnail": embed_thumbnail,
                "postprocessors": postprocessors,
            })

        return options

    def _log(self, message: str) -> None:
        if self.on_log:
            self.on_log(clean_ansi(message))
