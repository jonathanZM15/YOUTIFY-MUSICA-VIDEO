from typing import Callable, Optional
import customtkinter as ctk
from ui.theme import Colors


class DownloadCard(ctk.CTkFrame):
    """Tarjeta de entrada moderna y minimalista con controles estilizados."""

    def __init__(
        self,
        parent,
        on_format_change: Callable[[str], None],
        on_url_modified: Optional[Callable[[str], None]] = None,
    ):
        super().__init__(
            parent,
            fg_color=Colors.CARD_BG,
            corner_radius=12,
            border_width=1,
            border_color=Colors.BORDER,
        )
        self.pack(fill="x", padx=36, pady=(0, 10))
        self.on_url_modified = on_url_modified

        # ── Campo de URL con diseño minimalista ──
        self.url_var = ctk.StringVar()
        self.url_var.trace_add("write", self._on_trace_url)

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="x", padx=20, pady=18)

        ctk.CTkLabel(
            container,
            text="ENLACE DE YOUTUBE",
            font=("Segoe UI", 10, "bold"),
            text_color=Colors.TEXT_MUTED,
        ).pack(anchor="w", pady=(0, 6))

        self.url_entry = ctk.CTkEntry(
            container,
            textvariable=self.url_var,
            placeholder_text="Pega un enlace: https://www.youtube.com/watch?v=...",
            height=42,
            font=("Segoe UI", 13),
            corner_radius=8,
            border_width=1,
            border_color=Colors.BORDER_INPUT,
            fg_color=Colors.INPUT_BG,
            text_color=Colors.TEXT_PRIMARY,
        )
        self.url_entry.pack(fill="x", pady=(0, 14))

        # ── Selectores alineados horizontalmente ──
        options_row = ctk.CTkFrame(container, fg_color="transparent")
        options_row.pack(fill="x")

        # Formato
        ctk.CTkLabel(
            options_row,
            text="Formato",
            font=("Segoe UI", 12),
            text_color=Colors.TEXT_SECONDARY,
        ).pack(side="left", padx=(0, 8))

        self.format_menu = ctk.CTkComboBox(
            options_row,
            values=["MP3 (audio)", "MP4 (video)"],
            state="readonly",
            width=160,
            height=32,
            corner_radius=8,
            border_width=1,
            border_color=Colors.BORDER_INPUT,
            fg_color=Colors.INPUT_BG,
            button_color=Colors.BORDER_INPUT,
            button_hover_color=Colors.BORDER,
            font=("Segoe UI", 12),
            command=on_format_change,
        )
        self.format_menu.set("MP3 (audio)")
        self.format_menu.pack(side="left", padx=(0, 24))

        # Calidad
        ctk.CTkLabel(
            options_row,
            text="Calidad",
            font=("Segoe UI", 12),
            text_color=Colors.TEXT_SECONDARY,
        ).pack(side="left", padx=(0, 8))

        self.quality_menu = ctk.CTkComboBox(
            options_row,
            values=["Máxima", "1080p", "720p", "480p", "360p"],
            state="readonly",
            width=130,
            height=32,
            corner_radius=8,
            border_width=1,
            border_color=Colors.BORDER_INPUT,
            fg_color=Colors.INPUT_BG,
            button_color=Colors.BORDER_INPUT,
            button_hover_color=Colors.BORDER,
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
