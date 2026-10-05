from typing import Callable, Optional
import customtkinter as ctk
from ui.theme import Colors


class DownloadCard(ctk.CTkFrame):
    """Tarjeta contenedora de campos de entrada, formato y selección de calidad."""

    def __init__(
        self,
        parent,
        on_format_change: Callable[[str], None],
        on_url_modified: Optional[Callable[[str], None]] = None,
    ):
        super().__init__(
            parent,
            fg_color=Colors.CARD_BG,
            corner_radius=14,
            border_width=1,
            border_color=Colors.BORDER_SUBTLE,
        )
        self.pack(fill="x", padx=35, pady=(4, 6))
        self.on_url_modified = on_url_modified

        # Etiqueta de entrada
        ctk.CTkLabel(
            self,
            text="ENLACE DE YOUTUBE O PLAYLIST",
            font=("Segoe UI", 11, "bold"),
            text_color=Colors.TEXT_SUBTITLE,
        ).pack(anchor="w", padx=25, pady=(12, 4))

        # Campo de URL con detector de tecleo/pegado
        self.url_var = ctk.StringVar()
        self.url_var.trace_add("write", self._on_trace_url)

        self.url_entry = ctk.CTkEntry(
            self,
            textvariable=self.url_var,
            placeholder_text="https://www.youtube.com/watch?v=...",
            width=560,
            height=38,
            font=("Segoe UI", 13),
            corner_radius=10,
            border_color=Colors.BORDER_INPUT,
        )
        self.url_entry.pack(padx=25, pady=(0, 10))

        # Fila de opciones
        options_row = ctk.CTkFrame(self, fg_color="transparent")
        options_row.pack(fill="x", padx=25, pady=(0, 12))

        ctk.CTkLabel(options_row, text="Formato:", font=("Segoe UI", 12, "bold")).pack(side="left")
        self.format_menu = ctk.CTkComboBox(
            options_row,
            values=["MP3 (audio)", "MP4 (video)"],
            state="readonly",
            width=170,
            height=32,
            corner_radius=8,
            font=("Segoe UI", 12),
            command=on_format_change,
        )
        self.format_menu.set("MP3 (audio)")
        self.format_menu.pack(side="left", padx=(8, 30))

        ctk.CTkLabel(options_row, text="Calidad:", font=("Segoe UI", 12, "bold")).pack(side="left")
        self.quality_menu = ctk.CTkComboBox(
            options_row,
            values=["Máxima", "1080p", "720p", "480p", "360p"],
            state="readonly",
            width=125,
            height=32,
            corner_radius=8,
            font=("Segoe UI", 12),
        )
        self.quality_menu.set("Máxima")
        self.quality_menu.pack(side="left", padx=8)

    def _on_trace_url(self, *args):
        if self.on_url_modified:
            self.on_url_modified(self.get_url())

    def get_url(self) -> str:
        return self.url_entry.get().strip()

    def clear_url(self) -> None:
        self.url_entry.delete(0, "end")

    def get_format(self) -> str:
        return self.format_menu.get()

    def get_quality(self) -> str:
        return self.quality_menu.get()
