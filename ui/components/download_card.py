from typing import Callable, Optional
import customtkinter as ctk
from config.settings import AUDIO_QUALITIES, VIDEO_QUALITIES
from ui.theme import Colors
from ui.components.select_menu import SelectMenu


class DownloadCard(ctk.CTkFrame):
    def __init__(self, parent, on_format_change: Callable, on_url_modified: Optional[Callable] = None):
        super().__init__(parent, fg_color="transparent", corner_radius=0)
        self.pack(fill="x", padx=12, pady=(0, 8))
        self.on_format_change, self.on_url_modified = on_format_change, on_url_modified
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text="Enlace de YouTube", height=20, text_color=Colors.TEXT_SECONDARY,
            font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 7))
        self.url_entry = ctk.CTkEntry(self, placeholder_text="https://youtube.com/watch?v=…",
            height=38, corner_radius=8, border_color=Colors.BORDER_INPUT, fg_color=Colors.INPUT_BG,
            text_color=Colors.TEXT_PRIMARY, font=("Segoe UI", 12))
        self.url_entry.grid(row=1, column=0, sticky="ew")
        self.url_entry.bind("<KeyRelease>", lambda event: self._notify())
        self.url_entry.bind("<<Paste>>", lambda event: self.after(20, self._notify), add="+")
        tools = ctk.CTkFrame(self, fg_color="transparent")
        tools.grid(row=2, column=0, sticky="ew", pady=(5, 10))
        ctk.CTkLabel(tools, text="Videos · Shorts · Playlists", height=20, font=("Segoe UI", 10),
            text_color=Colors.TEXT_MUTED).pack(side="left")
        ctk.CTkButton(tools, text="Pegar", command=self._paste, width=60, height=25,
            fg_color=Colors.BTN_SECONDARY_BG, hover_color=Colors.BTN_SECONDARY_HOVER,
            text_color=Colors.BTN_SECONDARY_TEXT, font=("Segoe UI", 11)).pack(side="right")
        options = ctk.CTkFrame(self, fg_color="transparent")
        options.grid(row=3, column=0, sticky="ew", pady=(0, 12))
        options.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(options, text="Formato", height=20, font=("Segoe UI", 11, "bold"), text_color=Colors.TEXT_SECONDARY).grid(row=0, column=0, sticky="w", pady=(0, 4))
        ctk.CTkLabel(options, text="Calidad", height=20, font=("Segoe UI", 11, "bold"), text_color=Colors.TEXT_SECONDARY).grid(row=0, column=1, sticky="w", padx=(8, 0), pady=(0, 4))
        self.format_menu = SelectMenu(options, width=138, values=["MP3 (audio)", "MP4 (video)"], command=self._handle_format_change)
        self.format_menu.set("MP3 (audio)")
        self.format_menu.grid(row=1, column=0, sticky="ew", padx=(0, 6))
        self.quality_menu = SelectMenu(options, width=108, values=AUDIO_QUALITIES)
        self.quality_menu.set("Máxima")
        self.quality_menu.grid(row=1, column=1, sticky="ew", padx=(2, 0))
        self.thumbnail_var = ctk.BooleanVar(value=True)
        self.thumbnail_checkbox = ctk.CTkCheckBox(self, text="Incluir carátula", height=20, variable=self.thumbnail_var,
            font=("Segoe UI", 12), text_color=Colors.TEXT_SECONDARY, fg_color=Colors.PRIMARY,
            checkmark_color=Colors.PRIMARY_TEXT, hover_color=Colors.PRIMARY_HOVER, border_color=Colors.TEXT_MUTED,
            checkbox_width=18, checkbox_height=18)
        self.thumbnail_checkbox.grid(row=4, column=0, sticky="w")

    def _paste(self):
        try:
            self.set_url(self.clipboard_get().strip())
        except Exception:
            self.url_entry.focus_set()

    def set_url(self, url):
        self.url_entry.delete(0, "end")
        self.url_entry.insert(0, url)
        self._notify()

    def _notify(self):
        if self.on_url_modified:
            self.on_url_modified(self.get_url())

    def _handle_format_change(self, selection):
        self.quality_menu.configure(values=AUDIO_QUALITIES if selection.startswith("MP3") else VIDEO_QUALITIES)
        self.quality_menu.set("Máxima")
        if self.on_format_change:
            self.on_format_change(selection)

    def get_url(self): return self.url_entry.get().strip()
    def clear_url(self): self.set_url("")
    def get_format(self): return self.format_menu.get()
    def get_quality(self): return self.quality_menu.get()
    def get_embed_thumbnail(self): return self.thumbnail_var.get()
