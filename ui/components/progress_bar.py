import customtkinter as ctk
import math
from core.downloader import ANSI_ESCAPE_RE as _ANSI_RE, clean_ansi as _clean_text
from ui.theme import Colors


class ProgressBarWidget(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=Colors.CARD_BG, corner_radius=14, border_width=1, border_color=Colors.BORDER)
        self.pack(fill="x", pady=(0, 12))
        self.grid_columnconfigure(0, weight=1)
        self.status_badge = ctk.CTkLabel(self, text="Todo listo para tu próxima descarga", width=1, height=20, font=("Segoe UI", 12, "bold"), text_color=Colors.TEXT_PRIMARY, anchor="w")
        self.status_badge.grid(row=0, column=0, padx=20, pady=(10, 0), sticky="ew")
        self.percent = ctk.CTkLabel(self, text="0 % del archivo", height=28, font=("Segoe UI", 15, "bold"), text_color=Colors.TEXT_BRAND)
        self.percent.grid(row=0, column=1, rowspan=2, padx=20, pady=(8, 0))
        self.detail = ctk.CTkLabel(self, text="El progreso aparecerá aquí", width=1, height=18, font=("Segoe UI", 11), text_color=Colors.TEXT_MUTED, anchor="w")
        self.detail.grid(row=1, column=0, padx=20, sticky="ew")
        self.progress_bar = ctk.CTkProgressBar(self, height=6, corner_radius=3, progress_color=Colors.PRIMARY, fg_color=Colors.INPUT_BG)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=2, column=0, columnspan=2, padx=20, pady=(6, 10), sticky="ew")
        self.playlist_panel = ctk.CTkFrame(self, fg_color="transparent")
        self.playlist_panel.grid_columnconfigure(0, weight=1)
        self.playlist_label = ctk.CTkLabel(self.playlist_panel, text="Playlist", anchor="w", width=1, height=18,
            font=("Segoe UI", 11, "bold"), text_color=Colors.TEXT_PRIMARY)
        self.playlist_label.grid(row=0, column=0, sticky="ew")
        self.playlist_percent = ctk.CTkLabel(self.playlist_panel, text="0 %", height=20, font=("Segoe UI", 14, "bold"), text_color=Colors.TEXT_BRAND)
        self.playlist_percent.grid(row=0, column=1, padx=(12, 0))
        self.playlist_bar = ctk.CTkProgressBar(self.playlist_panel, height=6, corner_radius=3,
            progress_color=Colors.PRIMARY, fg_color=Colors.INPUT_BG)
        self.playlist_bar.set(0)
        self.playlist_bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        self._file_value = 0
        self._playlist_state = None
        self._playlist_visible = False

    def set_progress(self, value):
        value = min(1, max(0, value))
        if value == self._file_value: return
        self._file_value = value
        self.progress_bar.set(value)
        self.percent.configure(text=f"{round(value * 100)} % del archivo")

    def set_playlist_progress(self, progress):
        if progress == self._playlist_state: return
        self._playlist_state = progress.copy() if progress is not None else None
        if progress is None:
            self.playlist_panel.grid_remove()
            self._playlist_visible = False
            return
        if not self._playlist_visible:
            self.playlist_panel.grid(row=3, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 12))
            self._playlist_visible = True
        total = progress["total"]
        failed, cancelled = progress["failed"], progress["cancelled"]
        value = progress["value"]
        if progress["reading"]:
            text, percent = "Playlist · leyendo canciones…", "—"
        elif not total:
            text, percent = "Playlist · cancelada" if cancelled else "Playlist · no se pudo leer", "—"
        else:
            text = f'Playlist · {progress["completed"]} de {total} guardadas'
            if failed or cancelled:
                text = f'Playlist · {progress["done"]} de {total} finalizadas · {progress["completed"]} guardadas'
            if failed: text += f" · {failed} con error"
            if cancelled: text += f" · {cancelled} canceladas"
            percent = f"{100 if progress['done'] >= total else min(99, math.floor(value * 100))} %"
        self.playlist_label.configure(text=text)
        self.playlist_percent.configure(text=percent)
        self.playlist_bar.set(value)
        finished = total and progress["done"] >= total
        color = Colors.PROGRESS_ERROR if failed else Colors.TEXT_MUTED if cancelled else Colors.PROGRESS_SUCCESS if finished else Colors.PRIMARY
        self.playlist_bar.configure(progress_color=color)

    def set_active_download(self, current_item=1, total_items=1):
        self.progress_bar.configure(progress_color=Colors.PRIMARY)
        self.status_badge.configure(text="Descargando archivo", text_color=Colors.TEXT_PRIMARY)

    def set_converting(self, current_item=1, total_items=1):
        self.status_badge.configure(text="Convirtiendo y guardando…", text_color=Colors.STATUS_CONVERT_TEXT)
        self.detail.configure(text="Preparando el archivo final y sus metadatos")
        self.set_progress(0.97)

    def set_completed(self):
        self.progress_bar.configure(progress_color=Colors.PROGRESS_SUCCESS)
        self.status_badge.configure(text="Archivo guardado", text_color=Colors.STATUS_SUCCESS_TEXT)
        self.detail.configure(text="Ya puedes abrirlo desde la cola")
        self.set_progress(1)

    def set_error(self, message="No se pudo descargar el archivo"):
        self.progress_bar.configure(progress_color=Colors.PROGRESS_ERROR)
        self.status_badge.configure(text=message, text_color=Colors.STATUS_ERROR_TEXT)
        self.detail.configure(text="Consulta el detalle en la cola y vuelve a intentarlo")

    def reset_state(self):
        self.set_progress(0)
        self.status_badge.configure(text="Cola en pausa", text_color=Colors.TEXT_SECONDARY)
        self.detail.configure(text="Pulsa Iniciar cola cuando quieras continuar")
