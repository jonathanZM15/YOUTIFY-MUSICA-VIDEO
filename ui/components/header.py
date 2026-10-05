from pathlib import Path
import customtkinter as ctk
from PIL import Image
from ui.theme import Colors


class Header(ctk.CTkFrame):
    """Componente de cabecera con logotipo oficial y títulos de marca."""

    def __init__(self, parent, icon_path: Path):
        super().__init__(parent, fg_color=Colors.HEADER_BG, corner_radius=0)
        self.pack(fill="x")

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(pady=(16, 12))

        self._render_icon(inner, icon_path)

        ctk.CTkLabel(
            inner,
            text="YOUTIFY",
            font=("Segoe UI", 26, "bold"),
            text_color=Colors.TEXT_TITLE,
        ).pack(pady=(2, 0))

        ctk.CTkLabel(
            inner,
            text="Descarga música y videos de YouTube con alta fidelidad",
            font=("Segoe UI", 12),
            text_color=Colors.TEXT_SUBTITLE,
        ).pack(pady=(0, 2))

    def _render_icon(self, parent, icon_path: Path):
        try:
            if icon_path.exists():
                img = Image.open(str(icon_path))
                img = img.convert("RGBA").resize((52, 52), Image.LANCZOS)
                self.icon_image = ctk.CTkImage(light_image=img, dark_image=img, size=(52, 52))
                ctk.CTkLabel(parent, image=self.icon_image, text="").pack(pady=(2, 2))
        except Exception:
            pass
