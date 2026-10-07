import os
import random
import re
import shutil
import threading
import time
from pathlib import Path
from queue import Queue
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
from ui.components import (
    Header,
    DownloadCard,
    PreviewCard,
    ConsoleView,
    ProgressBarWidget,
    ModalDialog,
    UpdateDialog,
)

ANSI_ESCAPE_RE = re.compile(
    r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])|\x1b\[[0-9;]*[a-zA-Z]|\x1b\[[0-9;]*m"
)


def _clean_text(raw: str) -> str:
    if not raw:
        return ""
    return ANSI_ESCAPE_RE.sub("", str(raw)).strip()


class AppWindow(ctk.CTk):
    """Orquestador principal de la ventana y controlador de eventos de Youtify."""

    _queue_total_items: int = 0
    _queue_completed_items: int = 0

    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME}")
        self.geometry("700x710")
        self.resizable(False, False)

        # Fondo minimalista
        self.configure(fg_color=Colors.APP_BG)

        # Sistema de Cola Asíncrona (Download Queue)
        self.download_queue = Queue()
        self.is_downloading = False
        self._queue_total_items: int = 0
        self._queue_completed_items: int = 0
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

        # Verificación no bloqueante de entorno JavaScript (Node.js) para desafíos antibot
        self._check_nodejs_environment()

        # Actualizador silencioso de compatibilidad yt-dlp en segundo plano
        Updater.check_and_update_async(log_callback=self._handle_log)

        # Comprobación no intrusiva de versiones en GitHub Releases tras montar la ventana
        self.after(1500, self._check_app_updates)

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

    def _check_nodejs_environment(self) -> None:
        """Verifica de forma no bloqueante si Node.js está disponible en el PATH del sistema."""
        if not shutil.which("node"):
            self.console_view.append_log(
                "[!] Aviso: Node.js no detectado en el PATH del sistema.\n"
                "    Para resolver desafíos antibot de YouTube y mitigar errores 403 Forbidden,\n"
                "    se recomienda instalar Node.js LTS desde: https://nodejs.org/"
            )
        else:
            self.console_view.append_log("[✓] Entorno JavaScript: Node.js detectado para desafíos antibot.")

    def _build_layout(self) -> None:
        # 1. Cabecera minimalista limpia
        self.header = Header(self, icon_path=ICON_PATH)

        # 2. Tarjeta principal de formulario (URL + Formatos)
        self.download_card = DownloadCard(
            self,
            on_format_change=self._on_format_changed,
            on_url_modified=self._on_url_modified,
        )

        # 3. Tarjeta de previsualización (anclada bajo download_card)
        self.preview_card = PreviewCard(self)

        # 4. Destino y botón sutil de carpeta
        meta_bar = ctk.CTkFrame(self, fg_color="transparent")
        meta_bar.pack(fill="x", padx=36, pady=(4, 8))

        self.destination_label = ctk.CTkLabel(
            meta_bar,
            text="",
            text_color=Colors.TEXT_MUTED,
            font=("Segoe UI", 11),
            anchor="w",
        )
        self.destination_label.pack(side="left")

        self.open_folder_btn = ctk.CTkButton(
            meta_bar,
            text="Abrir carpeta",
            width=100,
            height=26,
            font=("Segoe UI", 11),
            fg_color="transparent",
            text_color=Colors.TEXT_SECONDARY,
            hover_color=Colors.CARD_BG,
            border_width=1,
            border_color=Colors.BORDER,
            corner_radius=6,
            command=self._open_destination_folder,
        )
        self.open_folder_btn.pack(side="right")

        # 5. Barra de acciones principales (Botones unificados)
        buttons_container = ctk.CTkFrame(self, fg_color="transparent")
        buttons_container.pack(fill="x", padx=36, pady=(2, 6))

        # Botón secundario: Añadir a cola (estilo outline/subtle)
        self.enqueue_btn = ctk.CTkButton(
            buttons_container,
            text="Añadir a la cola",
            height=40,
            font=("Segoe UI", 12, "bold"),
            fg_color=Colors.BTN_SECONDARY_BG,
            text_color=Colors.BTN_SECONDARY_TEXT,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            border_width=1,
            border_color=Colors.BTN_SECONDARY_BORDER,
            corner_radius=8,
            command=self.enqueue_download,
        )
        self.enqueue_btn.pack(side="left", fill="x", expand=True, padx=(0, 10))

        # Botón principal destacado: Descargar ahora
        self.download_btn = ctk.CTkButton(
            buttons_container,
            text="Descargar ahora",
            height=40,
            font=("Segoe UI", 12, "bold"),
            fg_color=Colors.PRIMARY,
            text_color="white",
            hover_color=Colors.PRIMARY_HOVER,
            corner_radius=8,
            command=self.start_download_task,
        )
        self.download_btn.pack(side="left", fill="x", expand=True)

        # 6. Barra de progreso ultra-fina
        self.progress_widget = ProgressBarWidget(self)

        # 7. Consola de registro
        self.console_view = ConsoleView(self)

        # Inicializar destino por defecto
        self._on_format_changed("MP3 (audio)")

    def _get_current_destination(self) -> Path:
        fmt = self.download_card.get_format()
        return MUSIC_DIR if fmt.startswith("MP3") else VIDEO_DIR

    def _on_format_changed(self, selection: str) -> None:
        dest = self._get_current_destination()
        self.destination_label.configure(text=f"Destino: {dest.name}")

    def _open_destination_folder(self) -> None:
        dest = self._get_current_destination()
        dest.mkdir(parents=True, exist_ok=True)
        os.startfile(dest)

    def _on_window_closing(self) -> None:
        if self.is_downloading or not self.download_queue.empty():
            if not ModalDialog.ask_confirm(
                self,
                title="Descargas en curso",
                message="Hay descargas activas o en cola de espera.\n¿Seguro que deseas salir y cancelarlas?",
            ):
                return
        self.destroy()

    # ── Previsualización Automática (Preview Inspector) ───────────
    def _on_url_modified(self, url: str) -> None:
        if self._inspect_timer:
            self.after_cancel(self._inspect_timer)
            self._inspect_timer = None

        clean_url = url.strip()
        if not SecurityValidator.is_valid_youtube_url(clean_url):
            self.preview_card.hide_preview()
            return

        self._inspect_timer = self.after(350, lambda: self._inspect_url_async(clean_url))

    def _inspect_url_async(self, target_url: str) -> None:
        def _task():
            current_url = self.download_card.get_url()
            if current_url != target_url:
                self.after(0, self.preview_card.hide_preview)
                return

            meta = DownloadEngine.extract_metadata_fast(target_url)

            def _apply_meta():
                if self.download_card.get_url() == target_url and meta:
                    self.preview_card.show_preview(
                        title=meta["title"],
                        channel=meta["channel"],
                        duration=f"{meta['duration']} canciones" if meta["is_playlist"] else meta["duration"],
                        thumbnail_url=meta["thumbnail"],
                        after_widget=self.download_card,
                    )
                else:
                    self.preview_card.hide_preview()

            self.after(0, _apply_meta)

        threading.Thread(target=_task, daemon=True).start()

    # ── Sistema de Cola y Descargas ──────────────────────────────
    def _add_to_queue(self, url: str, fmt: str, quality: str, destination: Path) -> None:
        """Expande playlists en descargas individuales o añade un video único a la cola."""
        playlist_urls = DownloadEngine.extract_playlist_urls(url)
        added_count = 0
        if playlist_urls:
            added_count = len(playlist_urls)
            self.console_view.append_log(f"[+] Playlist detectada: {added_count} videos. Añadiendo todos a la cola...")
            for item_url in playlist_urls:
                self.download_queue.put((item_url, fmt, quality, destination))
        else:
            added_count = 1
            self.download_queue.put((url, fmt, quality, destination))
            self.console_view.append_log(f"[+] Añadido a la cola: {url}")

        if not self.is_downloading:
            self._queue_total_items = self.download_queue.qsize()
            self._queue_completed_items = 0
            pending = self.download_queue.qsize()
            self.progress_widget.status_badge.configure(text=f"En cola: {pending} elemento(s)")
        else:
            self._queue_total_items += added_count

    def enqueue_download(self) -> None:
        url = self.download_card.get_url()
        if not self._validate_url(url):
            return

        fmt = self.download_card.get_format()
        quality = self.download_card.get_quality()
        destination = self._get_current_destination()

        self.download_card.clear_url()
        self.preview_card.hide_preview()

        self._add_to_queue(url, fmt, quality, destination)

        if not self.is_downloading:
            self._process_next_in_queue()

    def start_download_task(self) -> None:
        if self.is_downloading:
            self.enqueue_download()
            return

        url = self.download_card.get_url()
        if not self._validate_url(url):
            return

        fmt = self.download_card.get_format()
        quality = self.download_card.get_quality()
        destination = self._get_current_destination()

        self.download_card.clear_url()
        self.preview_card.hide_preview()

        self._add_to_queue(url, fmt, quality, destination)
        self._process_next_in_queue()

    def _validate_url(self, url: str) -> bool:
        if not url:
            ModalDialog.show_warning(
                self,
                title="Enlace requerido",
                message="Por favor ingresa o pega un enlace de YouTube antes de continuar.",
            )
            return False
        if not SecurityValidator.is_valid_youtube_url(url):
            ModalDialog.show_error(
                self,
                title="Enlace no válido",
                message="Ingresa un enlace verificado de YouTube o YouTube Music.\n\nEjemplo:\nhttps://www.youtube.com/watch?v=...",
            )
            return False
        return True

    def _process_next_in_queue(self, apply_delay: bool = False) -> None:
        if self.download_queue.empty():
            self.is_downloading = False
            self.download_btn.configure(state="normal", text="Descargar ahora")
            self.enqueue_btn.configure(state="normal")
            self.progress_widget.set_completed()
            self._queue_total_items = 0
            self._queue_completed_items = 0
            return

        if apply_delay:
            delay_sec = round(random.uniform(1.5, 4.0), 2)
            delay_ms = int(delay_sec * 1000)
            current_num = self._queue_completed_items + 1
            total_num = max(self._queue_total_items, current_num)

            # Durante la pausa antibot, el badge muestra el estado unificado activo
            self.progress_widget.set_active_download(current_num, total_num)
            self.console_view.append_log(
                f"[*] Pausa antibot preventiva de {delay_sec}s antes de la siguiente descarga..."
            )
            self.after(delay_ms, lambda: self._process_next_in_queue(apply_delay=False))
            return

        self.is_downloading = True
        if self._queue_total_items == 0:
            self._queue_total_items = self.download_queue.qsize()
            self._queue_completed_items = 0

        url, fmt, quality, destination = self.download_queue.get()
        self._current_task = url

        self.download_btn.configure(state="normal", text="Descargando...")

        # Posicionar el progreso inicial de este elemento en la barra continua acumulativa
        if self._queue_total_items > 0:
            starting_prog = self._queue_completed_items / self._queue_total_items
        else:
            starting_prog = 0.0
        self.progress_widget.set_progress(starting_prog)

        current_num = self._queue_completed_items + 1
        total_num = max(self._queue_total_items, current_num)
        self.progress_widget.set_active_download(current_num, total_num)
        self.console_view.append_log(f"─── Procesando: {fmt} (Restantes en cola: {self.download_queue.qsize()}) ───")

        threading.Thread(
            target=self._run_download_thread,
            args=(url, fmt, quality, destination),
            daemon=True,
        ).start()

    def _run_download_thread(self, url: str, fmt: str, quality: str, destination: Path) -> None:
        max_attempts = 2
        for attempt in range(1, max_attempts + 1):
            try:
                self.downloader.execute_download(
                    url=url,
                    format_type=fmt,
                    quality=quality,
                    destination_dir=destination,
                )
                self.after(0, self._on_single_download_success)
                return
            except Exception as error:
                err_msg = _clean_text(str(error))
                is_403 = "403" in err_msg or "Forbidden" in err_msg

                if is_403 and attempt < max_attempts:
                    retry_wait = round(random.uniform(5.0, 8.0), 1)
                    retry_log = (
                        f"[!] Error 403: Forbidden detectado (antibot de YouTube).\n"
                        f"[*] Reintentando automáticamente en {retry_wait}s (intento {attempt + 1}/{max_attempts})..."
                    )
                    self.after(0, lambda msg=retry_log: self.console_view.append_log(msg))
                    time.sleep(retry_wait)
                    continue

                if is_403:
                    err_msg += (
                        "\n\nYouTube solicitó verificación antibot (HTTP 403 Forbidden).\n"
                        "Se recomienda instalar Node.js LTS (https://nodejs.org/) para resolver este desafío."
                    )

                final_err = f"[ERROR] {err_msg}"
                self.after(0, lambda msg=final_err: self.console_view.append_log(msg))
                # El elemento falló definitivamente: contar como procesado para la barra continua
                self.after(0, self._on_item_failed_definitively)
                # Continuar procesando los siguientes elementos de la cola con pausa preventiva
                self.after(0, lambda: self._process_next_in_queue(apply_delay=True))
                self.after(
                    0,
                    lambda msg=err_msg: self._show_download_error(msg),
                )
                return

    def _on_item_failed_definitively(self) -> None:
        self._queue_completed_items += 1
        if self._queue_total_items > 0:
            overall = min(1.0, self._queue_completed_items / self._queue_total_items)
            self.progress_widget.set_progress(overall)

    def _show_download_error(self, message: str) -> None:
        try:
            if self.winfo_exists():
                ModalDialog.show_error(self, title="Error de descarga", message=message)
        except Exception:
            pass

    def _on_single_download_success(self) -> None:
        self._queue_completed_items += 1
        if self._queue_total_items > 0:
            overall = min(1.0, self._queue_completed_items / self._queue_total_items)
            self.progress_widget.set_progress(overall)
        else:
            self.progress_widget.set_progress(1.0)
        self.console_view.append_log("[✓] Archivo guardado y carátula incrustada con éxito.")
        self._process_next_in_queue(apply_delay=True)

    # ── Callbacks de eventos desde el motor ───────────────────────
    def _handle_progress(self, progress_float: float, pct_str: str, speed_str: str, eta_str: str) -> None:
        if self._queue_total_items > 0:
            overall = max(0.0, min(1.0, (self._queue_completed_items + progress_float) / self._queue_total_items))
        else:
            overall = max(0.0, min(1.0, progress_float))

        current_num = self._queue_completed_items + 1
        total_num = max(self._queue_total_items, current_num)

        self.after(0, lambda: self.progress_widget.set_progress(overall))
        self.after(0, lambda: self.progress_widget.set_active_download(current_num, total_num))

    def _handle_log(self, message: str) -> None:
        clean_msg = _clean_text(message)
        if clean_msg:
            self.after(0, lambda: self.console_view.append_log(clean_msg))

    def _handle_status(self, status_code: str, label: str) -> None:
        if status_code == "converting":
            current_num = self._queue_completed_items + 1
            total_num = max(self._queue_total_items, current_num)
            self.after(0, lambda: self.progress_widget.set_converting(current_num, total_num))

    # ── Actualizaciones de software ──────────────────────────────
    def _check_app_updates(self) -> None:
        """Lanza la verificación de versiones en GitHub en un hilo de fondo."""
        Updater.check_app_update_async(
            callback=lambda release_info: self.after(0, lambda: self._prompt_update(release_info))
        )

    def _prompt_update(self, release_info) -> None:
        """Presenta el diálogo modal de actualización de forma segura si la ventana sigue activa."""
        try:
            if self.winfo_exists():
                UpdateDialog(self, release_info=release_info)
        except Exception:
            pass
