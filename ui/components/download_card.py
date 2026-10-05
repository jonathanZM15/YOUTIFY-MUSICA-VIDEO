from typing import Callable, Optional
import customtkinter as ctk
from ui.theme import Colors


class DownloadCard(ctk.CTkFrame):
    """Tarjeta contenedora de campos de entrada, formato y selección de calidad con diseño pulido."""

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
            border_color=Colors.BORDER_CARD,
        )
        self.pack(fill="x", padx=30, pady=(12, 6))
        self.on_url_modified = on_url_modified

        # ── 1. Etiqueta superior del campo ──
        label_row = ctk.CTkFrame(self, fg_color="transparent")
        label_row.pack(fill="x", padx=22, pady=(16, 6))

        ctk.CTkLabel(
            label_row,
            text="ENLACE DE YOUTUBE O PLAYLIST",
            font=("Segoe UI", 11, "bold"),
            text_color=Colors.TEXT_MUTED,
        ).pack(side="left")

        # ── 2. Campo de URL moderno ──
        self.url_var = ctk.StringVar()
        self.url_var.trace_add("write", self._on_trace_url)

        input_frame = ctk.CTkFrame(self, fg_color="transparent")
        input_frame.pack(fill="x", padx=22, pady=(0, 14))

        self.url_entry = ctk.CTkEntry(
            input_frame,
            textvariable=self.url_var,
            placeholder_text="Pega aquí el enlace: https://www.youtube.com/watch?v=...",
            height=42,
            font=("Segoe UI", 13),
            corner_radius=10,
            border_width=1,
            border_color=Colors.BORDER_INPUT,
            fg_color=("white", "#090d16"),
        )
        self.url_entry.pack(fill="x")

        # ── 3. Fila de selectores (Formato y Calidad) con tarjetas visuales ──
        options_row = ctk.CTkFrame(self, fg_color="transparent")
        options_row.pack(fill="x", padx=22, pady=(0, 16))

        # Grupo Formato
        fmt_group = ctk.CTkFrame(options_row, fg_color="transparent")
        fmt_group.pack(side="left", padx=(0, 24))

        ctk.CTkLabel(
            fmt_group,
            text="Formato",
            font=("Segoe UI", 12, "bold"),
            text_color=Colors.TEXT_MAIN,
        ).pack(side="left", padx=(0, 8))

        self.format_menu = ctk.CTkComboBox(
            fmt_group,
            values=["MP3 (audio)", "MP4 (video)"],
            state="readonly",
            width=165,
            height=34,
            corner_radius=8,
            border_width=1,
            border_color=Colors.BORDER_INPUT,
            font=("Segoe UI", 12),
            command=on_format_change,
        )
        self.format_menu.set("MP3 (audio)")
        self.format_menu.pack(side="left")

        # Grupo Calidad
        qual_group = ctk.CTkFrame(options_row, fg_color="transparent")
        qual_group.pack(side="left")

        ctk.CTkLabel(
            qual_group,
            text="Calidad",
            font=("Segoe UI", 12, "bold"),
            text_color=Colors.TEXT_MAIN,
        ).pack(side="left", padx=(0, 8))

        self.quality_menu = ctk.CTkComboBox(
            qual_group,
            values=["Máxima", "1080p", "720p", "480p", "360p"],
            state="readonly",
            width=130,
            height=34,
            corner_radius=8,
            border_width=1,
            border_color=Colors.BORDER_INPUT,
            font=("Segoe UI", 12),
        )
        self.quality_menu.set("Máxima")
        self.quality_menu.pack(side="left")

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
