import os
import re
import shutil
import sys
import tempfile
import threading
import urllib.request
import zipfile
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk
from yt_dlp import YoutubeDL


ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class YoutifyApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Youtify | Descargas rápidas")
        self.geometry("700x650")
        self.resizable(False, False)
        self.directorio_actual = self._get_app_directory()
        self.ffmpeg_directory = self.directorio_actual / "ffmpeg"
        self.music_directory = self.directorio_actual / "Musica_Descargada"
        self.video_directory = self.directorio_actual / "descargas_videos"
        self.icon_path = self.directorio_actual / "icon.ico"
        if self.icon_path.exists():
            self.iconbitmap(str(self.icon_path))
        self._build_ui()

    @staticmethod
    def _get_app_directory():
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent
        return Path(__file__).resolve().parent

    def _build_ui(self):
        self.geometry("700x650")
        ctk.CTkLabel(
            self,
            text="YOUTIFY",
            font=("Arial", 26, "bold"),
            text_color=("#075985", "#bae6fd"),
        ).pack(pady=(18, 0))
        ctk.CTkLabel(
            self,
            text="Descarga música y videos de YouTube",
            font=("Arial", 13),
            text_color=("#475569", "#cbd5e1"),
        ).pack(pady=(0, 12))

        ctk.CTkLabel(
            self, text="ENLACE DE YOUTUBE", font=("Arial", 12, "bold")
        ).pack(anchor="w", padx=55, pady=(8, 4))
        self.url_entry = ctk.CTkEntry(
            self,
            placeholder_text="https://www.youtube.com/watch?v=...",
            width=590,
            height=40,
            font=("Arial", 13),
        )
        self.url_entry.pack(pady=(5, 12))

        options = ctk.CTkFrame(self, fg_color="transparent")
        options.pack(fill="x", padx=55)
        ctk.CTkLabel(options, text="Formato:").pack(side="left")
        self.format_menu = ctk.CTkComboBox(
            options, values=["MP3 (audio)", "MP4 (video)"], state="readonly", width=180
        )
        self.format_menu.set("MP3 (audio)")
        self.format_menu.pack(side="left", padx=(8, 35))
        ctk.CTkLabel(options, text="Calidad de video", font=("Arial", 12, "bold")).pack(side="left")
        self.quality_menu = ctk.CTkComboBox(
            options,
            values=["Máxima", "1080p", "720p", "480p", "360p"],
            state="readonly",
            width=130,
        )
        self.quality_menu.set("Máxima")
        self.quality_menu.pack(side="left", padx=8)

        self.destination_label = ctk.CTkLabel(
            self, text="", text_color=("#64748b", "#94a3b8"), font=("Arial", 11)
        )
        self.destination_label.pack(pady=(18, 10))
        self.format_menu.configure(command=self._update_destination)
        self._update_destination("MP3 (audio)")

        self.download_button = ctk.CTkButton(
            self,
            text="Descargar ahora",
            width=300,
            height=46,
            font=("Arial", 14, "bold"),
            command=self.start_download,
        )
        self.download_button.pack(pady=4)

        self.progress = ctk.CTkProgressBar(self, width=590, height=12)
        self.progress.set(0)
        self.progress.pack(pady=(18, 4))
        self.status_label = ctk.CTkLabel(
            self, text="Listo para descargar", text_color=("#475569", "#cbd5e1")
        )
        self.status_label.pack()
        self.status_box = ctk.CTkTextbox(
            self, width=590, height=175, font=("Consolas", 11)
        )
        self.status_box.pack(pady=(10, 18))
        self.status_box.insert("0.1", "Pega un enlace y elige el formato que necesitas.\n")
        self.status_box.configure(state="disabled")

    def _update_destination(self, selection):
        destination = (
            self.music_directory if selection.startswith("MP3") else self.video_directory
        )
        self.destination_label.configure(text=f"Destino: {destination}")

    def log(self, message):
        self.after(0, self._append_log, message)

    def _append_log(self, message):
        message = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", message)
        self.status_box.configure(state="normal")
        self.status_box.insert("end", message + "\n")
        self.status_box.see("end")
        self.status_box.configure(state="disabled")
        self.status_label.configure(text=message[:90])

    def start_download(self):
        url = self.url_entry.get().strip()
        if not url.startswith(("http://", "https://")):
            messagebox.showerror(
                "Enlace inválido", "Pega un enlace completo que empiece por http:// o https://."
            )
            return
        download_format = self.format_menu.get()
        quality = self.quality_menu.get()
        self.download_button.configure(state="disabled", text="Descargando...")
        self.progress.set(0)
        threading.Thread(
            target=self._download, args=(url, download_format, quality), daemon=True
        ).start()

    def _download(self, url, download_format, quality):
        is_audio = download_format.startswith("MP3")
        destination = self.music_directory if is_audio else self.video_directory
        try:
            destination.mkdir(parents=True, exist_ok=True)
            self.log(f"[+] Destino: {destination}")
            ffmpeg_directory = self._ensure_ffmpeg()
            options = self._build_options(
                is_audio, destination, ffmpeg_directory, quality
            )
            self.log("[+] Conectando con YouTube...")
            with YoutubeDL(options) as downloader:
                downloader.download([url])
            self.log("[OK] Descarga finalizada correctamente.")
            self.after(0, self._download_completed)
        except Exception as error:
            message = str(error)
            if "403" in message or "Forbidden" in message:
                message += (
                    "\n\nActualiza yt-dlp e instala Node.js LTS. "
                    "YouTube está rechazando el cliente por un desafío de seguridad."
                )
            self.log(f"[ERROR] {message}")
            self.after(0, lambda: messagebox.showerror("Error de descarga", message))
        finally:
            self.after(0, lambda: self.download_button.configure(
                state="normal", text="Descargar ahora"
            ))

    def _download_completed(self):
        self.url_entry.delete(0, "end")
        self.progress.set(1)
        self.status_label.configure(text="Descarga completada. Listo para un nuevo enlace.")
        messagebox.showinfo("Completado", "La descarga terminó correctamente.")

    def _build_options(self, is_audio, destination, ffmpeg_directory, quality=None):
        options = {
            "outtmpl": str(destination / "%(title)s.%(ext)s"),
            "windowsfilenames": True,
            "restrictfilenames": True,
            "noplaylist": False,
            "retries": 10,
            "fragment_retries": 10,
            "socket_timeout": 30,
            "http_headers": {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 Chrome/131.0 Safari/537.36"
                )
            },
            "progress_hooks": [self._progress_hook],
            "ffmpeg_location": str(ffmpeg_directory),
        }
        if shutil.which("node"):
            options["js_runtimes"] = {"node": {}}
            options["remote_components"] = {"ejs": ["github"]}
        if is_audio:
            options.update(
                {
                    "format": "bestaudio/best",
                    "postprocessors": [
                        {
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": "mp3",
                            "preferredquality": "0",
                        }
                    ],
                }
            )
        else:
            height = {"1080p": 1080, "720p": 720, "480p": 480, "360p": 360}.get(
                quality
            )
            selector = (
                f"bestvideo[height<={height}]+bestaudio/best[height<={height}]"
                if height
                else "bestvideo+bestaudio/best"
            )
            options.update(
                {
                    "format": selector,
                    "merge_output_format": "mp4",
                }
            )
        return options

    def _ensure_ffmpeg(self):
        ffmpeg = self.ffmpeg_directory / "ffmpeg.exe"
        ffprobe = self.ffmpeg_directory / "ffprobe.exe"
        if ffmpeg.exists() and ffprobe.exists():
            return self.ffmpeg_directory
        self.log("[*] Descargando FFmpeg...")
        self.ffmpeg_directory.mkdir(parents=True, exist_ok=True)
        archive = Path(tempfile.gettempdir()) / "youtify_ffmpeg.zip"
        url = (
            "https://github.com/BtbN/FFmpeg-Builds/releases/download/"
            "latest/ffmpeg-master-latest-win64-gpl.zip"
        )
        try:
            urllib.request.urlretrieve(url, archive)
            with zipfile.ZipFile(archive) as compressed:
                for member in compressed.namelist():
                    if member.endswith(("bin/ffmpeg.exe", "bin/ffprobe.exe")):
                        with compressed.open(member) as source, open(
                            self.ffmpeg_directory / Path(member).name, "wb"
                        ) as target:
                            shutil.copyfileobj(source, target)
        finally:
            archive.unlink(missing_ok=True)
        if not ffmpeg.exists() or not ffprobe.exists():
            raise RuntimeError("No se pudieron obtener ffmpeg.exe y ffprobe.exe.")
        return self.ffmpeg_directory

    def _progress_hook(self, data):
        if data.get("status") == "downloading":
            percent = data.get("_percent_str", "0%").strip()
            speed = data.get("_speed_str", "0B/s").strip()
            self.log(f"Descargando: {percent} - {speed}")
            try:
                progress = float(
                    percent.replace("%", "").replace(",", ".").strip()
                ) / 100
                self.after(0, lambda: self.progress.set(max(0, min(1, progress))))
            except ValueError:
                pass
        elif data.get("status") == "finished":
            self.log("[*] Archivo recibido; procesando...")


if __name__ == "__main__":
    YoutifyApp().mainloop()
