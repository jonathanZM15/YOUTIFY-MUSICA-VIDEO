import os
import threading
from pathlib import Path
from queue import Queue
from tkinter import messagebox
import customtkinter as ctk

from config.settings import (
    APP_NAME,
    ICON_PATH,
    MUSIC_DIR,
    VIDEO_DIR,
)
from core.validator import SecurityValidator
from core.downloader import DownloadEngine
from core.updater import Updater
from ui.theme import Colors
from ui.components import Header, DownloadCard, PreviewCard, ConsoleView, ProgressBarWidget


class AppWindow(ctk.CTk):
    """Orquestador principal de la ventana y controlador de eventos de Youtify."""

    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} | Descargas rápidas")
        self.geometry("700x750")
        self.resizable(False, False)

        # Sistema de Cola Asíncrona (Download Queue)
        self.download_queue = Queue()
        self.is_downloading = False
        self._current_task = None
        self._inspect_timer = None

        # Motor desacoplado
        self.downloader = DownloadEngine(
            on_progress=self._handle_progress,
            on_log=self._handle_log,
            on_status=self._handle_status,
        )

        self._init_window_icon()
        self.protocol("WM_DELETE_WINDOW", self._on_window_closing)
        self._build_layout()

        # Actualizador silencioso de compatibilidad yt-dlp en segundo plano
        Updater.check_and_update_async(log_callback=self._handle_log)

    def _init_window_icon(self) -> None:
        if ICON_PATH.exists():
            try:
                self.iconbitmap(str(ICON_PATH))
            except Exception:
                pass
        self.after(50, self._apply_window_icon)

    def _apply_window_icon(self) -> None:
        try:
            if ICON_PATH.exists():
                self.iconbitmap(str(ICON_PATH))
        except Exception:
            pass

    def _build_layout(self) -> None:
        # 1. Cabecera
        self.header = Header(self, icon_path=ICON_PATH)

        # 2. Separador visual
        ctk.CTkFrame(
            self,
            height=2,
            fg_color=Colors.SEPARATOR,
            corner_radius=0,
        ).pack(fill="x", padx=40, pady=(0, 6))

        # 3. Tarjeta de controles (URL + Formatos) con listener de previsualización
        self.download_card = DownloadCard(
            self,
            on_format_change=self._on_format_changed,
            on_url_modified=self._on_url_modified,
        )

        # 4. Tarjeta de previsualización del video (Miniatura + Título)
        self.preview_card = PreviewCard(self)

        # 5. Destino y botones de acción
        self.destination_label = ctk.CTkLabel(
            self,
            text="",
            text_color=Colors.TEXT_MUTED,
            font=("Segoe UI", 11),
        )
        self.destination_label.pack(pady=(4, 2))

        buttons_container = ctk.CTkFrame(self, fg_color="transparent")
        buttons_container.pack(pady=(0, 4))

        self.open_folder_btn = ctk.CTkButton(
            buttons_container,
            text="📁  Abrir carpeta",
            width=150,
            height=38,
            font=("Segoe UI", 12, "bold"),
            fg_color=Colors.SECONDARY,
            text_color=Colors.TEXT_MAIN,
            hover_color=Colors.SECONDARY_HOVER,
            border_width=1,
            border_color=Colors.BORDER_BUTTON,
            corner_radius=10,
            command=self._open_destination_folder,
        )
        self.open_folder_btn.pack(side="left", padx=(0, 8))

        # Botón para añadir a cola
        self.enqueue_btn = ctk.CTkButton(
            buttons_container,
            text="➕  Añadir a cola",
            width=140,
            height=38,
            font=("Segoe UI", 12, "bold"),
            fg_color=Colors.SECONDARY,
            text_color=Colors.TEXT_MAIN,
            hover_color=Colors.SECONDARY_HOVER,
            border_width=1,
            border_color=Colors.BORDER_BUTTON,
            corner_radius=10,
            command=self.enqueue_download,
        )
        self.enqueue_btn.pack(side="left", padx=(0, 8))

        self.download_btn = ctk.CTkButton(
            buttons_container,
            text="⬇  Descargar ahora",
            width=190,
            height=42,
            font=("Segoe UI", 13, "bold"),
            fg_color=Colors.PRIMARY,
            text_color="white",
            hover_color=Colors.PRIMARY_HOVER,
            corner_radius=10,
            command=self.start_download_task,
        )
        self.download_btn.pack(side="left")

        # 6. Barra de progreso y badges
        self.progress_widget = ProgressBarWidget(self)

        # 7. Terminal de logs
        self.console_view = ConsoleView(self)

        # Inicializar destino por defecto
        self._on_format_changed("MP3 (audio)")

    def _get_current_destination(self) -> Path:
        fmt = self.download_card.get_format()
        return MUSIC_DIR if fmt.startswith("MP3") else VIDEO_DIR

    def _on_format_changed(self, selection: str) -> None:
        dest = self._get_current_destination()
        self.destination_label.configure(text=f"📂 Guardando en: {dest}")

    def _open_destination_folder(self) -> None:
        dest = self._get_current_destination()
        dest.mkdir(parents=True, exist_ok=True)
        os.startfile(dest)

    def _on_window_closing(self) -> None:
        if self.is_downloading or not self.download_queue.empty():
            if not messagebox.askyesno(
                "Descargas en curso",
                "Hay descargas activas o en cola.\n¿Seguro que deseas salir y cancelarlas?",
            ):
                return
        self.destroy()

    # ── Previsualización Automática (Preview Inspector) ───────────
    def _on_url_modified(self, url: str) -> None:
        if self._inspect_timer:
            self.after_cancel(self._inspect_timer)

        if not SecurityValidator.is_valid_youtube_url(url):
            self.preview_card.hide_preview()
            return

        # Debounce de 400ms para no saturar peticiones mientras se escribe
        self._inspect_timer = self.after(400, lambda: self._inspect_url_async(url))

    def _inspect_url_async(self, url: str) -> None:
        def _task():
            meta = DownloadEngine.extract_metadata_fast(url)
            if meta:
                self.after(0, lambda: self.preview_card.show_preview(
                    title=meta["title"],
                    channel=meta["channel"],
                    duration=f"{meta['duration']} canciones" if meta["is_playlist"] else meta["duration"],
                    thumbnail_url=meta["thumbnail"],
                ))
            else:
                self.after(0, self.preview_card.hide_preview)

        threading.Thread(target=_task, daemon=True).start()

    # ── Sistema de Cola y Descargas ──────────────────────────────
    def enqueue_download(self) -> None:
        url = self.download_card.get_url()
        if not self._validate_url(url):
            return

        fmt = self.download_card.get_format()
        quality = self.download_card.get_quality()
        destination = self._get_current_destination()

        self.download_queue.put((url, fmt, quality, destination))
        self.download_card.clear_url()
        self.preview_card.hide_preview()

        pending = self.download_queue.qsize()
        self.console_view.append_log(f"[+] Añadido a la cola: {url} (Pendientes: {pending})")
        self.progress_widget.status_badge.configure(text=f"📋 En cola: {pending} elemento(s)")

        if not self.is_downloading:
            self._process_next_in_queue()

    def start_download_task(self) -> None:
        if self.is_downloading:
            # Si ya hay una activa, lo encolamos directamente
            self.enqueue_download()
            return

        url = self.download_card.get_url()
        if not self._validate_url(url):
            return

        fmt = self.download_card.get_format()
        quality = self.download_card.get_quality()
        destination = self._get_current_destination()

        self.download_queue.put((url, fmt, quality, destination))
        self.download_card.clear_url()
        self.preview_card.hide_preview()
        self._process_next_in_queue()

    def _validate_url(self, url: str) -> bool:
        if not url:
            messagebox.showwarning("Enlace requerido", "Por favor pega un enlace de YouTube.")
            return False
        if not SecurityValidator.is_valid_youtube_url(url):
            messagebox.showerror(
                "Enlace no válido",
                "Ingresa un enlace válido de YouTube o YouTube Music.\n\n"
                "Ejemplo:\nhttps://www.youtube.com/watch?v=...",
            )
            return False
        return True

    def _process_next_in_queue(self) -> None:
        if self.download_queue.empty():
            self.is_downloading = False
            self.download_btn.configure(state="normal", text="⬇  Descargar ahora")
            self.progress_widget.set_completed()
            return

        self.is_downloading = True
        url, fmt, quality, destination = self.download_queue.get()
        self._current_task = url

        self.download_btn.configure(state="normal", text="⬇  Descargando...")
        self.progress_widget.set_progress(0)
        self.progress_widget.set_active_download("0%", "Iniciando...")
        self.console_view.append_log(f"─── Procesando: {fmt} (Restantes en cola: {self.download_queue.qsize()}) ───")

        threading.Thread(
            target=self._run_download_thread,
            args=(url, fmt, quality, destination),
            daemon=True,
        ).start()

    def _run_download_thread(self, url: str, fmt: str, quality: str, destination: Path) -> None:
        try:
            self.downloader.execute_download(
                url=url,
                format_type=fmt,
                quality=quality,
                destination_dir=destination,
            )
            self.after(0, self._on_single_download_success)
        except Exception as error:
            err_msg = str(error)
            if "403" in err_msg or "Forbidden" in err_msg:
                err_msg += "\n\nYouTube solicitó verificación antibot. Node.js LTS recomendado."
            self.console_view.append_log(f"[ERROR] {err_msg}")
            self.after(0, lambda: messagebox.showerror("Error de descarga", err_msg))
            self.after(0, self._process_next_in_queue)

    def _on_single_download_success(self) -> None:
        self.console_view.append_log("[✓] Archivo guardado y carátula incrustada con éxito.")
        self._process_next_in_queue()

    # ── Callbacks de eventos desde el motor ───────────────────────
    def _handle_progress(self, progress_float: float, pct_str: str, speed_str: str, eta_str: str) -> None:
        self.after(0, lambda: self.progress_widget.set_progress(progress_float))
        self.after(0, lambda: self.progress_widget.set_active_download(pct_str, speed_str))

    def _handle_log(self, message: str) -> None:
        self.after(0, lambda: self.console_view.append_log(message))

    def _handle_status(self, status_code: str, label: str) -> None:
        if status_code == "converting":
            self.after(0, self.progress_widget.set_converting)
