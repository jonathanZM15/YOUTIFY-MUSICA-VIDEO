import logging
import os
import threading
from pathlib import Path
from queue import Queue, Empty, Full, SimpleQueue
from tkinter import filedialog
import customtkinter as ctk

from config.settings import (APP_NAME, ICON_PATH, MUSIC_DIR, VIDEO_DIR, AUDIO_QUALITIES,
    VIDEO_QUALITIES, PREFERENCES_FILE, LOG_FILE, UPDATE_CHECK_INTERVAL_SEC)
from core.storage import JsonStore
from core.validator import SecurityValidator
from core.downloader import ANSI_ESCAPE_RE, DownloadEngine, clean_ansi as _clean_text
from core.download_manager import DownloadManager, ACTIVE, FINISHED
from core.updater import Updater
from core.runtime import javascript_options
from ui.theme import Colors
from ui.runtime import configure_runtime
from ui.components import Header, DownloadCard, PreviewCard, ConsoleView, ProgressBarWidget, ModalDialog
from ui.components.queue_view import QueueView


class AppWindow(ctk.CTk):
    """All widgets are accessed on the Tk thread; workers send data through a queue."""
    def __init__(self):
        configure_runtime()
        super().__init__()
        self._closing = False
        self._events = Queue(maxsize=500)
        self._calls = SimpleQueue()
        self._state_lock = threading.Lock()
        self._pending_queue = None
        self._pending_progress = None
        self._inspect_timer = None
        self._preview_busy = False
        self._preview_url = ""
        self._preview_title = ""
        self._preview_thread_url = ""
        self._last_jobs = []
        self._last_active = None
        self._last_finished = None
        self._render_revision = 0
        self._update_banner = None
        self._idle_polls = 0
        self._preferences = JsonStore(PREFERENCES_FILE)
        prefs = self._preferences.read({})
        self.prefs = prefs if isinstance(prefs, dict) else {}
        self._saved_prefs = self.prefs.copy()
        self._custom_destination = Path(self.prefs["destination"]) if isinstance(self.prefs.get("destination"), str) and self.prefs["destination"] else None
        self.title(APP_NAME)
        scale = self._get_window_scaling()
        available_width = int(self.winfo_screenwidth() / scale) - 60
        available_height = int(self.winfo_screenheight() / scale) - 90
        self.geometry(f"{min(1080, available_width)}x{min(760, available_height)}")
        self.minsize(min(880, available_width), min(570, available_height))
        self.configure(fg_color=Colors.APP_BG)
        ctk.set_appearance_mode({"Oscuro": "Dark", "Claro": "Light", "Sistema": "System"}.get(self.prefs.get("theme"), "Dark"))
        if ICON_PATH.exists():
            self.after(50, lambda: self.iconbitmap(str(ICON_PATH)))
        self.protocol("WM_DELETE_WINDOW", self._on_window_closing)
        self.header = Header(self, ICON_PATH, self.prefs.get("theme", "Oscuro"), self._change_theme)
        self.header.pack_forget()
        self.header.grid(row=0, column=0, sticky="ew", padx=24, pady=(16, 12))
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._build_layout()
        self.manager = DownloadManager(self._emit)
        self._render_queue(self.manager.queue_state())
        self.after(100, self._drain_events)
        self.after(1500, self._check_app_updates)
        Updater.check_and_update_async(log_callback=lambda msg: self._emit("log", msg))
        runtime = javascript_options()["js_runtimes"]
        self._emit("log", "[✓] Motor JavaScript disponible." if runtime else "[!] No hay motor JavaScript. Usa el instalador completo o instala Node.js LTS.")
        self.bind("<Control-Return>", lambda event: self.start_download_task())
        self.bind("<Control-l>", lambda event: self.download_card.url_entry.focus_set())
        self.report_callback_exception = self._report_ui_error

    def _build_layout(self):
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.grid(row=1, column=0, sticky="nsew", padx=24, pady=(0, 12))
        self.content.grid_columnconfigure(1, weight=1)
        self.content.grid_rowconfigure(0, weight=1)
        self.left_panel = ctk.CTkFrame(self.content, width=320, fg_color=Colors.CARD_BG,
            corner_radius=14, border_width=1, border_color=Colors.BORDER)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        self.left_panel.grid_propagate(False)
        self.left_panel.grid_columnconfigure(0, weight=1)
        self.left_panel.grid_rowconfigure(0, weight=1)
        self.body = ctk.CTkScrollableFrame(self.left_panel, width=292, fg_color=Colors.CARD_BG,
            corner_radius=10, scrollbar_button_color=Colors.BORDER)
        self.body.grid(row=0, column=0, sticky="nsew", padx=4, pady=(6, 0))
        ctk.CTkLabel(self.body, text="Nueva descarga", font=("Segoe UI", 18, "bold"),
            text_color=Colors.TEXT_PRIMARY).pack(anchor="w", padx=12, pady=(6, 12))
        self.download_card = DownloadCard(self.body, self._on_format_changed, self._on_url_modified)
        fmt = self.prefs.get("format", "MP3 (audio)")
        if fmt not in ["MP3 (audio)", "MP4 (video)"]:
            fmt = "MP3 (audio)"
        self.download_card.format_menu.set(fmt)
        qualities = AUDIO_QUALITIES if fmt.startswith("MP3") else VIDEO_QUALITIES
        self.download_card.quality_menu.configure(values=qualities)
        quality = self.prefs.get("quality", "Máxima")
        self.download_card.quality_menu.set(quality if quality in qualities else "Máxima")
        self.download_card.thumbnail_var.set(bool(self.prefs.get("embed_thumbnail", True)))
        self.preview_card = PreviewCard(self.body, dispatch=lambda fn: self._emit("call", fn), compact=True)
        self.input_feedback = ctk.CTkLabel(self.body, text="Los enlaces se revisan automáticamente.", width=1,
            wraplength=265, justify="left", anchor="w", font=("Segoe UI", 10), text_color=Colors.TEXT_MUTED)
        # Feedback becomes visible when a link is being inspected.
        destination = ctk.CTkFrame(self.body, fg_color="transparent")
        destination.pack(fill="x", padx=12, pady=(8, 4))
        ctk.CTkLabel(destination, text="Guardar en", font=("Segoe UI", 11, "bold"),
            text_color=Colors.TEXT_SECONDARY).pack(anchor="w")
        self.destination_label = ctk.CTkLabel(destination, text="", width=1, font=("Segoe UI", 10),
            text_color=Colors.TEXT_MUTED, anchor="w", justify="left", height=18)
        self.destination_label.pack(fill="x", pady=(0, 4))
        folder_tools = ctk.CTkFrame(destination, fg_color="transparent")
        folder_tools.pack(fill="x")
        for text, command, width in [("Cambiar", self._choose_custom_folder, 78),
                ("Abrir", self._open_destination_folder, 66), ("Restablecer", self._reset_destination, 90)]:
            ctk.CTkButton(folder_tools, text=text, command=command, height=27, width=width,
                fg_color=Colors.BTN_SECONDARY_BG, hover_color=Colors.BTN_SECONDARY_HOVER,
                text_color=Colors.BTN_SECONDARY_TEXT, font=("Segoe UI", 10)).pack(side="left", padx=(0, 5))
        actions = ctk.CTkFrame(self.left_panel, fg_color=Colors.CARD_BG, corner_radius=0)
        actions.grid(row=1, column=0, sticky="ew", padx=18, pady=(10, 14))
        self.download_btn = ctk.CTkButton(actions, text="Descargar ahora", command=self.start_download_task,
            height=38, font=("Segoe UI", 13, "bold"), fg_color=Colors.PRIMARY,
            hover_color=Colors.PRIMARY_HOVER, text_color=Colors.PRIMARY_TEXT, corner_radius=8)
        self.download_btn.pack(fill="x", pady=(0, 6))
        self.enqueue_btn = ctk.CTkButton(actions, text="Añadir a la cola", command=self.enqueue_download,
            height=30, font=("Segoe UI", 12), fg_color=Colors.BTN_SECONDARY_BG,
            hover_color=Colors.BTN_SECONDARY_HOVER, text_color=Colors.BTN_SECONDARY_TEXT, corner_radius=8)
        self.enqueue_btn.pack(fill="x")
        self.workspace = ctk.CTkFrame(self.content, fg_color=Colors.CARD_BG, corner_radius=14,
            border_width=1, border_color=Colors.BORDER)
        self.workspace.grid(row=0, column=1, sticky="nsew")
        self.workspace.grid_columnconfigure(0, weight=1)
        self.workspace.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(self.workspace, text="Tus descargas", font=("Segoe UI", 20, "bold"),
            text_color=Colors.TEXT_PRIMARY).grid(row=0, column=0, sticky="w", padx=20, pady=(18, 4))
        self.tabs = ctk.CTkTabview(self.workspace, fg_color=Colors.CARD_BG, corner_radius=10, anchor="w",
            segmented_button_fg_color=Colors.INPUT_BG, segmented_button_selected_color=Colors.BTN_SECONDARY_BG,
            segmented_button_selected_hover_color=Colors.BTN_SECONDARY_HOVER,
            segmented_button_unselected_color=Colors.INPUT_BG, segmented_button_unselected_hover_color=Colors.CARD_HOVER,
            text_color=Colors.TEXT_PRIMARY)
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 10))
        queue_tab = self.tabs.add("Cola")
        log_tab = self.tabs.add("Actividad")
        queue_header = ctk.CTkFrame(queue_tab, fg_color="transparent")
        queue_header.pack(fill="x", padx=6, pady=(4, 10))
        self.queue_summary = ctk.CTkLabel(queue_header, text="Sin descargas", text_color=Colors.TEXT_MUTED,
            font=("Segoe UI", 11), anchor="w", width=1)
        self.queue_summary.pack(fill="x", pady=(0, 9))
        toolbar = ctk.CTkFrame(queue_header, fg_color="transparent")
        toolbar.pack(fill="x")
        self.pause_btn = ctk.CTkButton(toolbar, text="Iniciar cola", width=108, height=29, font=("Segoe UI", 11),
            command=self._toggle_pause, fg_color=Colors.BTN_SECONDARY_BG, text_color=Colors.BTN_SECONDARY_TEXT,
            hover_color=Colors.BTN_SECONDARY_HOVER)
        self.pause_btn.pack(side="left")
        ctk.CTkButton(toolbar, text="Limpiar finalizadas", width=125, height=29, font=("Segoe UI", 10),
            command=lambda: self.manager.clear_finished(), fg_color="transparent", text_color=Colors.TEXT_MUTED,
            hover_color=Colors.CARD_HOVER).pack(side="right")
        self.queue_view = QueueView(queue_tab, lambda jid: self.manager.cancel(jid),
            lambda jid: self.manager.retry(jid), self._open_job)
        self.console_view = ConsoleView(log_tab)
        ctk.CTkButton(log_tab, text="Abrir diagnóstico", command=self._open_logs, height=26,
            fg_color="transparent", text_color=Colors.TEXT_MUTED, hover_color=Colors.CARD_HOVER,
            font=("Segoe UI", 10)).pack(anchor="w", padx=12, pady=(0, 8))
        dock = ctk.CTkFrame(self, fg_color="transparent")
        dock.grid(row=2, column=0, sticky="ew", padx=24)
        self.progress_widget = ProgressBarWidget(dock)
        self.progress_widget.pack_configure(pady=0)
        self._on_format_changed(fmt, save=False)
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=26, pady=(6, 10))
        ctk.CTkLabel(footer, text="Un archivo a la vez. Tú controlas la cola.", text_color=Colors.TEXT_MUTED,
            font=("Segoe UI", 10)).pack(side="left")
        ctk.CTkLabel(footer, text="Ctrl + L  Enlace     Ctrl + Enter  Descargar", text_color=Colors.TEXT_MUTED,
            font=("Segoe UI", 10)).pack(side="right")

    def _emit(self, kind, data):
        if self._closing: return
        if kind == "call":
            self._calls.put(data)
        elif kind in {"queue", "progress"}:
            with self._state_lock:
                if kind == "queue": self._pending_queue = data
                else: self._pending_progress = data
        else:
            try: self._events.put_nowait((kind, data))
            except Full: pass  # File diagnostics remain available; UI logs are bounded.

    def _drain_events(self):
        if self._closing: return
        with self._state_lock:
            latest_queue, latest_progress = self._pending_queue, self._pending_progress
            self._pending_queue = self._pending_progress = None
        activity = latest_queue is not None or latest_progress is not None
        for _ in range(10):
            try: callback = self._calls.get_nowait()
            except Empty: break
            activity = True
            try:
                callback()
            except Exception:
                logging.getLogger(__name__).exception("Error al aplicar una respuesta de segundo plano")
        logs = []
        for _ in range(150):
            try: kind, data = self._events.get_nowait()
            except Empty: break
            activity = True
            if kind == "log": logs.append(data)
        if logs: self.console_view.append_logs(logs)
        if latest_queue is not None: self._render_queue(latest_queue)
        if latest_progress is not None:
            job = next((j for j in self._last_jobs if j["id"] == latest_progress["id"]), None)
            if job and job["status"] == "downloading" and latest_progress.get("revision", 0) >= self._render_revision:
                self._render_revision = latest_progress.get("revision", self._render_revision)
                self.progress_widget.set_progress(latest_progress["value"])
                self.progress_widget.set_playlist_progress(latest_progress.get("playlist"))
                speed, eta = latest_progress["speed"], latest_progress["eta"]
                self.progress_widget.detail.configure(text=f"{speed}" + (f"   ·   Restante: {eta}" if eta else ""))
        self._idle_polls = 0 if activity else self._idle_polls + 1
        self.after(60 if self._idle_polls < 5 else 250, self._drain_events)

    def _render_queue(self, data):
        revision = data.get("revision", self._render_revision)
        if revision < self._render_revision:
            return
        self._render_revision = revision
        jobs, paused = data["jobs"], data["paused"]
        self.progress_widget.set_playlist_progress(data.get("playlist"))
        self._last_jobs = jobs
        self.queue_view.render(jobs)
        counts = {state: sum(j["status"] == state for j in jobs) for state in ["pending", "resolving", "completed", "failed", "cancelled"]}
        active = next((j for j in jobs if j["status"] in ACTIVE), None)
        waiting = counts["pending"] + counts["resolving"]
        parts = [f"{waiting} en espera", f'{counts["completed"]} guardadas']
        if counts["failed"]: parts.append(f'{counts["failed"]} con error')
        if counts["cancelled"]: parts.append(f'{counts["cancelled"]} canceladas')
        self.queue_summary.configure(text="   ·   ".join(parts) if jobs else "Tu próxima descarga empieza aquí")
        self.pause_btn.configure(text="Iniciar cola" if paused else "Pausar cola", state="normal" if waiting or active else "disabled")
        if active:
            if self._last_active != active["id"]:
                self.progress_widget.set_progress(0)
                self.progress_widget.detail.configure(text="Conectando con YouTube…")
            if active["status"] == "converting": self.progress_widget.set_converting()
            else:
                self.progress_widget.set_active_download()
                if "current_progress" in data:
                    self.progress_widget.set_progress(data["current_progress"])
            self.progress_widget.status_badge.configure(text=("Guardando: " if active["status"] == "converting" else "Descargando: ") + active["title"][:66])
            self._last_active = active["id"]
        else:
            finished = [j for j in jobs if j["status"] in FINISHED]
            latest = finished[-1] if finished else None
            if latest and (latest["id"], latest["status"]) != self._last_finished:
                if latest["status"] == "completed": self.progress_widget.set_completed()
                elif latest["status"] == "failed": self.progress_widget.set_error()
                else:
                    self.progress_widget.reset_state()
                    self.progress_widget.status_badge.configure(text="Descarga cancelada")
                    self.progress_widget.detail.configure(text="Puedes reintentarlo desde la cola")
                self._last_finished = (latest["id"], latest["status"])
            if waiting and paused: self.progress_widget.reset_state()
            if counts["resolving"]:
                self.progress_widget.status_badge.configure(text="Leyendo playlist…")
                self.progress_widget.detail.configure(text="Puedes seguir usando la aplicación")
            if not waiting and counts["failed"] and not active:
                self.progress_widget.set_error(f'Cola finalizada · {counts["failed"]} con error')
            self._last_active = None
            if not jobs:
                self.progress_widget.set_progress(0)
                self.progress_widget.status_badge.configure(text="Todo listo para tu próxima descarga", text_color=Colors.TEXT_PRIMARY)
                self.progress_widget.detail.configure(text="El progreso aparecerá aquí")
                self._last_finished = None

    def _save_preferences(self):
        try:
            self.prefs.update(format=self.download_card.get_format(), quality=self.download_card.get_quality(),
                embed_thumbnail=self.download_card.get_embed_thumbnail(), destination=str(self._custom_destination) if self._custom_destination else "")
            if self.prefs != self._saved_prefs:
                self._preferences.write(self.prefs)
                self._saved_prefs = self.prefs.copy()
        except OSError:
            self._emit("log", "[!] No se pudieron guardar las preferencias.")

    def _change_theme(self, selection):
        ctk.set_appearance_mode({"Oscuro": "Dark", "Claro": "Light", "Sistema": "System"}[selection])
        self.prefs["theme"] = selection
        self._save_preferences()

    def _get_current_destination(self):
        return self._custom_destination or (MUSIC_DIR if self.download_card.get_format().startswith("MP3") else VIDEO_DIR)

    def _on_format_changed(self, selection, save=True):
        if not hasattr(self, "destination_label"): return
        dest = self._get_current_destination()
        label = str(dest)
        self.destination_label.configure(text="…" + label[-62:] if len(label) > 63 else label)
        if save: self._save_preferences()

    def _choose_custom_folder(self):
        dest = self._get_current_destination()
        folder = filedialog.askdirectory(title="Seleccionar carpeta de descarga", initialdir=str(dest if dest.exists() else Path.home()))
        if folder:
            self._custom_destination = Path(folder)
            self._on_format_changed(self.download_card.get_format())

    def _reset_destination(self):
        self._custom_destination = None
        self._on_format_changed(self.download_card.get_format())

    def _open_destination_folder(self):
        try:
            dest = self._get_current_destination()
            dest.mkdir(parents=True, exist_ok=True)
            os.startfile(dest)
        except OSError as error:
            ModalDialog.show_error(self, "No se pudo abrir la carpeta", str(error))

    def _open_job(self, job):
        target = Path(job["filepath"]) if job["filepath"] else Path(job["destination"])
        try: os.startfile(target)
        except OSError: ModalDialog.show_warning(self, "Archivo no encontrado", "El archivo se ha movido o eliminado. Abre la carpeta de destino para buscarlo.")

    def _open_logs(self):
        try:
            LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            LOG_FILE.touch(exist_ok=True)
            os.startfile(LOG_FILE)
        except OSError as error: self._emit("log", str(error))

    def _toggle_pause(self):
        if self.manager.paused: self.manager.resume()
        else:
            self.manager.pause()
            self._emit("log", "[i] Cola en pausa. El archivo actual terminará antes de detenerse.")

    def _submit(self, start):
        url = self.download_card.get_url()
        if not SecurityValidator.is_valid_youtube_url(url):
            ModalDialog.show_warning(self, "Revisa el enlace", "Pega un enlace de video, Shorts o playlist de YouTube para continuar.")
            return
        try:
            self.manager.submit(url, self.download_card.get_format(), self.download_card.get_quality(),
                self._get_current_destination(), self.download_card.get_embed_thumbnail(),
                self._preview_title if self._preview_url == url else "", start=start)
            self._save_preferences()
            self.download_card.clear_url()
            self.preview_card.hide_preview()
            self.tabs.set("Cola")
        except (ValueError, OSError) as error: ModalDialog.show_error(self, "No se pudo añadir", str(error))

    def enqueue_download(self): self._submit(False)
    def start_download_task(self): self._submit(True)

    def _on_url_modified(self, url):
        if self._inspect_timer:
            self.after_cancel(self._inspect_timer)
            self._inspect_timer = None
        self._preview_url = url
        self._preview_title = ""
        self.preview_card.hide_preview()
        valid = SecurityValidator.is_valid_youtube_url(url)
        self.input_feedback.configure(
            text="Buscando detalles del enlace…" if valid else ("Videos, Shorts o playlists de YouTube." if url else "Los enlaces se revisan automáticamente."),
            text_color=Colors.TEXT_MUTED)
        if url:
            self.input_feedback.pack(fill="x", padx=12, pady=(0, 6), after=self.download_card)
        else:
            self.input_feedback.pack_forget()
        if valid:
            self._inspect_timer = self.after(650, lambda: self._inspect_url_async(url))

    def _inspect_url_async(self, url):
        self._inspect_timer = None
        if self._preview_busy or url != self._preview_url: return
        self._preview_busy = True
        self._preview_thread_url = url
        def task():
            meta = DownloadEngine.extract_metadata_fast(url)
            self._emit("call", lambda: self._apply_preview(url, meta))
        threading.Thread(target=task, daemon=True, name="video-preview").start()

    def _apply_preview(self, url, meta):
        self._preview_busy = False
        if url != self._preview_url:
            if SecurityValidator.is_valid_youtube_url(self._preview_url): self._inspect_url_async(self._preview_url)
            return  # An old response must never hide a newer preview.
        if meta:
            self.input_feedback.configure(text="Enlace listo para añadir.", text_color=Colors.SUCCESS)
            self._preview_title = meta["title"]
            duration = f'{meta["duration"]} elementos' if meta["is_playlist"] else meta["duration"]
            self.preview_card.show_preview(meta["title"], meta["channel"], duration, meta["thumbnail"], self.download_card)
        else:
            self.input_feedback.configure(text="Vista previa no disponible. Puedes intentar descargar el enlace.", text_color=Colors.TEXT_MUTED)

    def _check_app_updates(self):
        if self._closing:
            return
        Updater.check_app_update_async(lambda release: self._emit("call", lambda: self._show_update_ready(release)))
        self.after(UPDATE_CHECK_INTERVAL_SEC * 1000, self._check_app_updates)

    def _show_update_ready(self, release):
        if self._closing or not Updater.should_notify(release.tag_name):
            return
        if self._update_banner:
            self._update_banner.destroy()
        banner = self._update_banner = ctk.CTkFrame(self, fg_color=Colors.BTN_SECONDARY_BG, corner_radius=8)
        banner.grid(row=4, column=0, sticky="ew", padx=24, pady=(0, 8))
        ctk.CTkLabel(banner, text=f"Versión {release.version} lista. Se aplicará al volver a abrir Youtify.",
            font=("Segoe UI", 11), text_color=Colors.TEXT_PRIMARY).pack(side="left", padx=12, pady=6)
        ctk.CTkButton(banner, text="Entendido", width=85, height=26, command=banner.grid_remove,
            fg_color=Colors.PRIMARY, text_color=Colors.PRIMARY_TEXT).pack(side="right", padx=10)
        Updater._update_state(last_notified_tag=release.tag_name)

    def _report_ui_error(self, exc, value, traceback):
        logging.getLogger(__name__).error("Error de interfaz", exc_info=(exc, value, traceback))
        self._emit("log", f"[ERROR] {value}")

    def _on_window_closing(self):
        if any(j["status"] in ACTIVE for j in self._last_jobs):
            if not ModalDialog.ask_confirm(self, "Cerrar Youtify", "La descarga actual se detendrá. La cola quedará guardada para continuar cuando vuelvas a abrir Youtify."):
                return
        self._save_preferences()
        self._closing = True
        self.manager.close()
        self.destroy()
