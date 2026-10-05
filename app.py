import gc
import os
import re
import shutil
import sys
import tempfile
import threading
import time
import urllib.request
import zipfile
from pathlib import Path
from tkinter import messagebox
from urllib.parse import urlparse

import customtkinter as ctk

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

# ── Constantes ───────────────────────────────────────────────────
_MAX_LOG_LINES = 200
_PROGRESS_THROTTLE_SEC = 0.35
_VALID_HOSTS = frozenset({
    "youtube.com", "www.youtube.com", "m.youtube.com",
    "music.youtube.com", "youtu.be", "www.youtu.be",
})
_ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_QUALITY_MAP = {"1080p": 1080, "720p": 720, "480p": 480, "360p": 360}
_FFMPEG_URL = (
    "https://github.com/BtbN/FFmpeg-Builds/releases/download/"
    "latest/ffmpeg-master-latest-win64-gpl.zip"
)


class YoutifyApp(ctk.CTk):
    """Aplicación principal de Youtify — diseño moderno, seguro y optimizado."""

    __slots__ = (
        "is_downloading", "directorio_actual", "ffmpeg_directory",
        "music_directory", "video_directory", "icon_path",
        "url_entry", "format_menu", "quality_menu",
        "destination_label", "open_folder_button", "download_button",
        "progress", "status_badge", "status_box",
        "_header_icon", "_log_line_count", "_last_progress_time",
    )

    def __init__(self):
        super().__init__()
        self.title("Youtify | Descargas rápidas")
        self.geometry("700x730")
        self.resizable(False, False)

        self.is_downloading = False
        self._log_line_count = 0
        self._last_progress_time = 0.0
        self._header_icon = None

        self.directorio_actual = self._get_app_directory()
        local_app_data = Path(
            os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")
        )
        self.ffmpeg_directory = local_app_data / "Youtify" / "ffmpeg"
        downloads_directory = Path.home() / "Downloads" / "Youtify"
        self.music_directory = downloads_directory / "Musica_Descargada"
        self.video_directory = downloads_directory / "descargas_videos"

        self.icon_path = self.directorio_actual / "icon.ico"
        if self.icon_path.exists():
            try:
                self.iconbitmap(str(self.icon_path))
            except Exception:
                pass

        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        self._build_ui()

    # ── Utilidades estáticas ─────────────────────────────────────
    @staticmethod
    def _get_app_directory() -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent
        return Path(__file__).resolve().parent

    @staticmethod
    def _is_valid_youtube_url(url: str) -> bool:
        try:
            parsed = urlparse(url.strip())
            if parsed.scheme not in ("http", "https"):
                return False
            host = (parsed.hostname or "").lower()
            return host in _VALID_HOSTS or host.endswith(".youtube.com")
        except Exception:
            return False

    # ── Ciclo de vida ────────────────────────────────────────────
    def _on_closing(self):
        if self.is_downloading:
            if not messagebox.askyesno(
                "Descarga en curso",
                "Hay una descarga activa en segundo plano.\n¿Estás seguro de que deseas salir?"
            ):
                return
        self.destroy()

    # ── Interfaz gráfica ─────────────────────────────────────────
    def _build_ui(self):
        self.after(50, self._apply_icon)

        # ── Header con Logo ──────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color=("white", "#141426"), corner_radius=0)
        header.pack(fill="x")

        header_inner = ctk.CTkFrame(header, fg_color="transparent")
        header_inner.pack(pady=(16, 12))

        self._load_header_icon(header_inner)

        ctk.CTkLabel(
            header_inner, text="YOUTIFY",
            font=("Segoe UI", 26, "bold"),
            text_color=("#0369a1", "#38bdf8"),
        ).pack(pady=(2, 0))
        ctk.CTkLabel(
            header_inner, text="Descarga música y videos de YouTube con alta fidelidad",
            font=("Segoe UI", 12),
            text_color=("#64748b", "#94a3b8"),
        ).pack(pady=(0, 2))

        # ── Separador ───────────────────────────────────────────
        ctk.CTkFrame(
            self, height=2, fg_color=("#e2e8f0", "#27273f"), corner_radius=0
        ).pack(fill="x", padx=40, pady=(0, 8))

        # ── Tarjeta principal de controles ──────────────────────
        card = ctk.CTkFrame(
            self, fg_color=("#f8fafc", "#16162a"),
            corner_radius=14, border_width=1,
            border_color=("#e2e8f0", "#27273f"),
        )
        card.pack(fill="x", padx=35, pady=(4, 8))

        ctk.CTkLabel(
            card, text="ENLACE DE YOUTUBE O PLAYLIST",
            font=("Segoe UI", 11, "bold"),
            text_color=("#475569", "#94a3b8"),
        ).pack(anchor="w", padx=25, pady=(14, 4))

        self.url_entry = ctk.CTkEntry(
            card, placeholder_text="https://www.youtube.com/watch?v=...",
            width=560, height=40,
            font=("Segoe UI", 13), corner_radius=10,
            border_color=("#cbd5e1", "#3b3b5c"),
        )
        self.url_entry.pack(padx=25, pady=(0, 12))

        # Fila de opciones: Formato + Calidad
        options = ctk.CTkFrame(card, fg_color="transparent")
        options.pack(fill="x", padx=25, pady=(0, 14))

        ctk.CTkLabel(options, text="Formato:", font=("Segoe UI", 12, "bold")).pack(side="left")
        self.format_menu = ctk.CTkComboBox(
            options, values=["MP3 (audio)", "MP4 (video)"],
            state="readonly", width=170, height=32,
            corner_radius=8, font=("Segoe UI", 12),
        )
        self.format_menu.set("MP3 (audio)")
        self.format_menu.pack(side="left", padx=(8, 30))

        ctk.CTkLabel(options, text="Calidad:", font=("Segoe UI", 12, "bold")).pack(side="left")
        self.quality_menu = ctk.CTkComboBox(
            options, values=["Máxima", "1080p", "720p", "480p", "360p"],
            state="readonly", width=125, height=32,
            corner_radius=8, font=("Segoe UI", 12),
        )
        self.quality_menu.set("Máxima")
        self.quality_menu.pack(side="left", padx=8)

        # ── Destino y Botones de acción ─────────────────────────
        self.destination_label = ctk.CTkLabel(
            self, text="", text_color=("#64748b", "#7c8da6"), font=("Segoe UI", 11)
        )
        self.destination_label.pack(pady=(6, 4))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(0, 6))

        self.open_folder_button = ctk.CTkButton(
            btn_frame, text="📁  Abrir carpeta",
            width=180, height=38,
            font=("Segoe UI", 12, "bold"),
            fg_color=("#e2e8f0", "#252544"),
            text_color=("#1e293b", "#e2e8f0"),
            hover_color=("#cbd5e1", "#3b3b5c"),
            border_width=1, border_color=("#94a3b8", "#3b3b5c"),
            corner_radius=10, command=self._open_download_folder,
        )
        self.open_folder_button.pack(side="left", padx=(0, 12))

        self.download_button = ctk.CTkButton(
            btn_frame, text="⬇  Descargar ahora",
            width=220, height=44,
            font=("Segoe UI", 14, "bold"),
            fg_color=("#0284c7", "#0ea5e9"), text_color="white",
            hover_color=("#0369a1", "#0284c7"),
            corner_radius=10, command=self.start_download,
        )
        self.download_button.pack(side="left")

        self.format_menu.configure(command=self._update_destination)
        self._update_destination("MP3 (audio)")

        # ── Barra de Progreso ────────────────────────────────────
        prog_frame = ctk.CTkFrame(self, fg_color="transparent")
        prog_frame.pack(fill="x", padx=40, pady=(10, 2))

        self.progress = ctk.CTkProgressBar(
            prog_frame, width=560, height=10, corner_radius=5,
            progress_color=("#0284c7", "#0ea5e9"),
        )
        self.progress.set(0)
        self.progress.pack()

        # Badge interactivo de estado
        self.status_badge = ctk.CTkLabel(
            self, text="Listo para descargar",
            fg_color=("#f1f5f9", "#1e1e36"),
            text_color=("#475569", "#94a3b8"),
            font=("Segoe UI", 12, "bold"),
            corner_radius=10,
            padx=14, pady=4,
        )
        self.status_badge.pack(pady=(6, 6))

        # ── Consola moderna estilo Terminal ─────────────────────
        console_container = ctk.CTkFrame(
            self, fg_color=("#f1f5f9", "#0c0c1b"),
            corner_radius=10, border_width=1,
            border_color=("#e2e8f0", "#27273f"),
        )
        console_container.pack(fill="x", padx=35, pady=(2, 14))

        # Barra de título de la consola
        console_top = ctk.CTkFrame(console_container, fg_color="transparent", height=24)
        console_top.pack(fill="x", padx=10, pady=(6, 2))

        ctk.CTkLabel(
            console_top, text="● REGISTRO DE DESCARGA",
            font=("Segoe UI", 10, "bold"),
            text_color=("#0284c7", "#38bdf8"),
        ).pack(side="left")

        clear_btn = ctk.CTkButton(
            console_top, text="Limpiar", width=60, height=20,
            font=("Segoe UI", 10),
            fg_color="transparent", hover_color=("#e2e8f0", "#1e1e36"),
            text_color=("#64748b", "#94a3b8"),
            command=self._clear_logs,
        )
        clear_btn.pack(side="right")

        self.status_box = ctk.CTkTextbox(
            console_container, width=590, height=130,
            font=("Consolas", 11),
            fg_color="transparent",
            text_color=("#334155", "#cbd5e1"),
            border_width=0,
        )
        self.status_box.pack(padx=8, pady=(0, 6))
        self.status_box.insert("0.1", "[*] Pega un enlace y presiona Descargar ahora.\n")
        self.status_box.configure(state="disabled")

    # ── Icono ────────────────────────────────────────────────────
    def _apply_icon(self):
        try:
            if self.icon_path.exists():
                self.iconbitmap(str(self.icon_path))
        except Exception:
            pass

    def _load_header_icon(self, parent):
        try:
            from PIL import Image
            if self.icon_path.exists():
                icon_img = Image.open(str(self.icon_path))
                icon_img = icon_img.convert("RGBA").resize((52, 52), Image.LANCZOS)
                self._header_icon = ctk.CTkImage(
                    light_image=icon_img, dark_image=icon_img, size=(52, 52)
                )
                ctk.CTkLabel(parent, image=self._header_icon, text="").pack(pady=(2, 2))
        except Exception:
            pass

    # ── Acciones de UI ───────────────────────────────────────────
    def _update_destination(self, selection):
        dest = self.music_directory if selection.startswith("MP3") else self.video_directory
        self.destination_label.configure(text=f"📂 Guardando en: {dest}")

    def _open_download_folder(self):
        dest = (
            self.music_directory
            if self.format_menu.get().startswith("MP3")
            else self.video_directory
        )
        dest.mkdir(parents=True, exist_ok=True)
        os.startfile(dest)

    def _clear_logs(self):
        self.status_box.configure(state="normal")
        self.status_box.delete("1.0", "end")
        self.status_box.configure(state="disabled")
        self._log_line_count = 0

    # ── Logging optimizado (buffer rotativo) ─────────────────────
    def log(self, message: str):
        self.after(0, self._append_log, message)

    def _append_log(self, message: str):
        message = _ANSI_RE.sub("", message).strip()
        if not message:
            return

        self.status_box.configure(state="normal")
        self._log_line_count += 1
        if self._log_line_count > _MAX_LOG_LINES:
            self.status_box.delete("1.0", "2.0")
            self._log_line_count -= 1

        self.status_box.insert("end", message + "\n")
        self.status_box.see("end")
        self.status_box.configure(state="disabled")

    # ── Descarga ─────────────────────────────────────────────────
    def start_download(self):
        if self.is_downloading:
            messagebox.showwarning(
                "Descarga en curso",
                "Ya hay una descarga activa. Espera a que finalice."
            )
            return

        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Enlace requerido", "Pega un enlace de YouTube.")
            return

        if not self._is_valid_youtube_url(url):
            messagebox.showerror(
                "Enlace no válido",
                "Ingresa un enlace válido de YouTube o YouTube Music.\n\n"
                "Ejemplo:\nhttps://www.youtube.com/watch?v=..."
            )
            return

        fmt = self.format_menu.get()
        quality = self.quality_menu.get()
        self.is_downloading = True
        self._last_progress_time = 0.0

        # UI en estado activo
        self.download_button.configure(state="disabled", text="⏳ Descargando...")
        self.progress.configure(progress_color=("#0284c7", "#0ea5e9"))
        self.progress.set(0)
        self.status_badge.configure(
            text="⏳ Descargando y convirtiendo medios...",
            text_color=("#0284c7", "#38bdf8"),
            fg_color=("#e0f2fe", "#0c2b4e"),
        )
        self.log(f"─── Iniciando descarga: {fmt} ───")

        threading.Thread(
            target=self._download, args=(url, fmt, quality), daemon=True
        ).start()

    def _download(self, url: str, download_format: str, quality: str):
        is_audio = download_format.startswith("MP3")
        destination = self.music_directory if is_audio else self.video_directory
        try:
            destination.mkdir(parents=True, exist_ok=True)
            self.log(f"[+] Carpeta de destino: {destination.name}")
            ffmpeg_dir = self._ensure_ffmpeg()
            opts = self._build_options(is_audio, destination, ffmpeg_dir, quality)
            self.log("[+] Conectando con los servidores de YouTube...")

            from yt_dlp import YoutubeDL
            with YoutubeDL(opts) as dl:
                dl.download([url])

            self.after(0, self._download_completed)
        except Exception as error:
            msg = str(error)
            if "403" in msg or "Forbidden" in msg:
                msg += (
                    "\n\nActualiza yt-dlp e instala Node.js LTS. "
                    "YouTube rechaza el cliente por un desafío de seguridad."
                )
            self.log(f"[ERROR] {msg}")
            self.after(0, self._download_failed, msg)
        finally:
            self.is_downloading = False
            self.after(0, lambda: self.download_button.configure(
                state="normal", text="⬇  Descargar ahora"
            ))
            gc.collect()

    def _download_completed(self):
        self.url_entry.delete(0, "end")
        self.progress.configure(progress_color=("#16a34a", "#22c55e"))
        self.progress.set(1.0)
        self.status_badge.configure(
            text="✨ ¡Descarga completada con éxito!",
            text_color=("#15803d", "#4ade80"),
            fg_color=("#dcfce7", "#052e16"),
        )
        self.log("[✓] Proceso finalizado con éxito. Archivo guardado correctamente.")

    def _download_failed(self, msg: str):
        self.progress.configure(progress_color=("#dc2626", "#ef4444"))
        self.status_badge.configure(
            text="❌ Error durante la descarga",
            text_color=("#b91c1c", "#f87171"),
            fg_color=("#fee2e2", "#450a0a"),
        )
        messagebox.showerror("Error de descarga", msg)

    # ── Opciones de yt-dlp ───────────────────────────────────────
    def _build_options(self, is_audio, destination, ffmpeg_dir, quality=None):
        opts = {
            "outtmpl": str(destination / "%(title)s.%(ext)s"),
            "windowsfilenames": True,
            "restrictfilenames": True,
            "noplaylist": False,
            "retries": 10,
            "fragment_retries": 10,
            "socket_timeout": 30,
            "concurrent_fragment_downloads": 4,
            "buffersize": 1024 * 64,
            "http_chunk_size": 1024 * 1024 * 10,
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
        }
        if shutil.which("node"):
            opts["js_runtimes"] = {"node": {}}
            opts["remote_components"] = {"ejs": ["github"]}
        if is_audio:
            opts.update({
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "0",
                }],
            })
        else:
            height = _QUALITY_MAP.get(quality)
            selector = (
                f"bestvideo[height<={height}]+bestaudio/best[height<={height}]"
                if height else "bestvideo+bestaudio/best"
            )
            opts.update({"format": selector, "merge_output_format": "mp4"})
        return opts

    # ── FFmpeg ────────────────────────────────────────────────────
    def _ensure_ffmpeg(self) -> Path:
        local_dir = self.directorio_actual / "ffmpeg"
        if (local_dir / "ffmpeg.exe").exists() and (local_dir / "ffprobe.exe").exists():
            return local_dir

        sys_ff = shutil.which("ffmpeg")
        sys_fp = shutil.which("ffprobe")
        if sys_ff and sys_fp:
            return Path(sys_ff).resolve().parent

        ffmpeg = self.ffmpeg_directory / "ffmpeg.exe"
        ffprobe = self.ffmpeg_directory / "ffprobe.exe"
        if ffmpeg.exists() and ffprobe.exists():
            return self.ffmpeg_directory

        self.log("[*] FFmpeg no encontrado. Descargando componentes...")
        self.ffmpeg_directory.mkdir(parents=True, exist_ok=True)
        archive = Path(tempfile.gettempdir()) / "youtify_ffmpeg.zip"
        try:
            req = urllib.request.Request(
                _FFMPEG_URL,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req, timeout=120) as resp, \
                    open(archive, "wb") as f_out:
                shutil.copyfileobj(resp, f_out)
            with zipfile.ZipFile(archive) as zf:
                for member in zf.namelist():
                    if member.endswith(("bin/ffmpeg.exe", "bin/ffprobe.exe")):
                        with zf.open(member) as src, open(
                            self.ffmpeg_directory / Path(member).name, "wb"
                        ) as dst:
                            shutil.copyfileobj(src, dst)
        finally:
            archive.unlink(missing_ok=True)
        if not ffmpeg.exists() or not ffprobe.exists():
            raise RuntimeError("No se pudieron obtener ffmpeg.exe y ffprobe.exe.")
        return self.ffmpeg_directory

    # ── Progress hook (limpio, profesional y throttled) ──────────
    def _progress_hook(self, data: dict):
        status = data.get("status")
        if status == "downloading":
            now = time.monotonic()
            if now - self._last_progress_time < _PROGRESS_THROTTLE_SEC:
                return
            self._last_progress_time = now

            pct = data.get("_percent_str", "0%").strip()
            spd = data.get("_speed_str", "—").strip()
            eta = data.get("_eta_str", "").strip()

            msg = f"⚡ Descargando: {pct} a {spd}"
            if eta:
                msg += f" (tiempo restante: {eta})"
            self.log(msg)

            try:
                val = float(pct.replace("%", "").replace(",", ".").strip()) / 100
                val = max(0.0, min(1.0, val))
                self.after(0, lambda v=val: self.progress.set(v))
                self.after(0, lambda p=pct, s=spd: self.status_badge.configure(
                    text=f"Descargando {p} • {s}",
                    text_color=("#0284c7", "#38bdf8"),
                    fg_color=("#e0f2fe", "#0c2b4e"),
                ))
            except ValueError:
                pass
        elif status == "finished":
            self.after(0, lambda: self.status_badge.configure(
                text="🔄 Ensamblando y convirtiendo audio/video...",
                text_color=("#d97706", "#fbbf24"),
                fg_color=("#fef3c7", "#451a03"),
            ))
            self.log("[*] Descarga recibida; procesando conversión con FFmpeg...")


if __name__ == "__main__":
    YoutifyApp().mainloop()
