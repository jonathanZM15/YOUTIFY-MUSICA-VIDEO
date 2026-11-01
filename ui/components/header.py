from pathlib import Path
import customtkinter as ctk
from PIL import Image
from config.settings import APP_VERSION
from ui.theme import Colors
from ui.components.select_menu import SelectMenu


class Header(ctk.CTkFrame):
    def __init__(self, parent, icon_path: Path, theme="Oscuro", on_theme=None):
        super().__init__(parent, fg_color="transparent", corner_radius=0)
        self.pack(fill="x", padx=24, pady=(16, 14))
        try:
            with Image.open(icon_path) as source:
                self.logo = ctk.CTkImage(source.convert("RGBA"), size=(34, 34))
            ctk.CTkLabel(self, text="", image=self.logo).pack(side="left", padx=(0, 10))
        except OSError:
            pass
        ctk.CTkLabel(self, text="Youtify", font=("Segoe UI", 22, "bold"), text_color=Colors.TEXT_PRIMARY).pack(side="left")
        ctk.CTkLabel(self, text=APP_VERSION, font=("Segoe UI", 10), text_color=Colors.TEXT_SECONDARY,
            fg_color=Colors.CARD_BG, corner_radius=5, padx=7, pady=2).pack(side="left", padx=10)
        self.theme_menu = SelectMenu(self, values=["Oscuro", "Claro", "Sistema"], command=on_theme,
            width=106, height=30, font=("Segoe UI", 11), fg_color=Colors.CARD_BG,
            text_color=Colors.TEXT_SECONDARY)
        self.theme_menu.set(theme)
        self.theme_menu.pack(side="right")
        ctk.CTkLabel(self, text="Tu música y tus videos, en un solo lugar", font=("Segoe UI", 11),
            text_color=Colors.TEXT_MUTED).pack(side="right", padx=18)
