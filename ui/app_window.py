import os
import threading
from pathlib import Path
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
from ui.theme import Colors
from ui.components import Header, DownloadCard, ConsoleView, ProgressBarWidget


class AppWindow(ctk.CTk):
    """Orquestador principal de la ventana y controlador de eventos de Youtify."""

    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} | Descargas rápidas")
        self.geometry("700x730")
        self.resizable(False, False)

        # Candados de estado concurrentes
        self.is_downloading = False

        # Motor de descarga desacoplado con callbacks
        self.downloader = DownloadEngine(
            on_progress=self._handle_progress,
            on_log=self._handle_log,
            on_status=self._handle_status,
        )

        self._init_window_icon()
        self.protocol("WM_DELETE_WINDOW", self._on_window_closing)
        self._build_layout()

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
        ).pack(fill="x", padx=40, pady=(0, 8))

        # 3. Tarjeta de controles (URL + Formatos)
        self.download_card = DownloadCard(self, on_format_change=self._on_format_changed)

        # 4. Destino y botones de acción
        self.destination_label = ctk.CTkLabel(
            self,
            text="",
            text_color=Colors.TEXT_MUTED,
            font=("Segoe UI", 11),
        )
        self.destination_label.pack(pady=(6, 4))

        buttons_container = ctk.CTkFrame(self, fg_color="transparent")
        buttons_container.pack(pady=(0, 6))

        self.open_folder_btn = ctk.CTkButton(
            buttons_container,
            text="📁  Abrir carpeta",
            width=180,
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
        self.open_folder_btn.pack(side="left", padx=(0, 12))

        self.download_btn = ctk.CTkButton(
            buttons_container,
            text="⬇  Descargar ahora",
            width=220,
            height=44,
            font=("Segoe UI", 14, "bold"),
            fg_color=Colors.PRIMARY,
            text_color="white",
            hover_color=Colors.PRIMARY_HOVER,
            corner_radius=10,
            command=self.start_download_task,
        )
        self.download_btn.pack(side="left")

        # 5. Barra de progreso y badges
        self.progress_widget = ProgressBarWidget(self)

        # 6. Terminal de logs
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
        if self.is_downloading:
            if not messagebox.askyesno(
                "Descarga en curso",
                "Hay una descarga activa en segundo plano.\n¿Estás seguro de que deseas salir?",
            ):
                return
        self.destroy()

    # ── Controlador de Descargas ─────────────────────────────────
    def start_download_task(self) -> None:
        if self.is_downloading:
            messagebox.showwarning("Descarga en curso", "Ya hay una descarga activa. Espera a que finalice.")
            return

        url = self.download_card.get_url()
        if not url:
            messagebox.showwarning("Enlace requerido", "Por favor pega un enlace de YouTube.")
            return

        # Validación con SecurityValidator
        if not SecurityValidator.is_valid_youtube_url(url):
            messagebox.showerror(
                "Enlace no válido",
                "Ingresa un enlace válido de YouTube o YouTube Music.\n\n"
                "Ejemplo:\nhttps://www.youtube.com/watch?v=...",
            )
            return

        fmt = self.download_card.get_format()
        quality = self.download_card.get_quality()
        destination = self._get_current_destination()

        self.is_downloading = True
        self.download_btn.configure(state="disabled", text="⏳ Descargando...")
        self.progress_widget.set_progress(0)
        self.progress_widget.set_active_download("0%", "Conectando...")
        self.console_view.append_log(f"─── Iniciando descarga: {fmt} ───")

        # Ejecución en hilo separado
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
            self.after(0, self._on_download_success)
        except Exception as error:
            err_msg = str(error)
            if "403" in err_msg or "Forbidden" in err_msg:
                err_msg += (
                    "\n\nYouTube está solicitando verificación JS. "
                    "Asegúrate de tener Node.js instalado o actualiza yt-dlp."
                )
            self.console_view.append_log(f"[ERROR] {err_msg}")
            self.after(0, self._on_download_error, err_msg)
        finally:
            self.is_downloading = False
            self.after(0, lambda: self.download_btn.configure(state="normal", text="⬇  Descargar ahora"))

    def _on_download_success(self) -> None:
        self.download_card.clear_url()
        self.progress_widget.set_completed()
        self.console_view.append_log("[✓] Proceso finalizado con éxito. Archivo guardado correctamente.")

    def _on_download_error(self, err_msg: str) -> None:
        self.progress_widget.set_error("Error durante la descarga")
        messagebox.showerror("Error de descarga", err_msg)

    # ── Callbacks de eventos desde el motor ───────────────────────
    def _handle_progress(self, progress_float: float, pct_str: str, speed_str: str, eta_str: str) -> None:
        self.after(0, lambda: self.progress_widget.set_progress(progress_float))
        self.after(0, lambda: self.progress_widget.set_active_download(pct_str, speed_str))

    def _handle_log(self, message: str) -> None:
        self.after(0, lambda: self.console_view.append_log(message))

    def _handle_status(self, status_code: str, label: str) -> None:
        if status_code == "converting":
            self.after(0, self.progress_widget.set_converting)
