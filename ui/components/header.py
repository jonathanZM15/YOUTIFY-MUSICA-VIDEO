from pathlib import Path
import customtkinter as ctk
from PIL import Image
from ui.theme import Colors


class Header(ctk.CTkFrame):
    """Cabecera minimalista: logo nítido, tipografía limpia y sin cajas innecesarias."""

    def __init__(self, parent, icon_path: Path):
        super().__init__(
            parent,
            fg_color="transparent",
            corner_radius=0,
        )
        self.pack(fill="x", padx=36, pady=(24, 16))

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="x")

        # Fila horizontal: Logo + Info agrupada
        left_box = ctk.CTkFrame(inner, fg_color="transparent")
        left_box.pack(side="left")

        self._render_icon(left_box, icon_path)

        text_group = ctk.CTkFrame(left_box, fg_color="transparent")
        text_group.pack(side="left", padx=(14, 0))

        title_line = ctk.CTkFrame(text_group, fg_color="transparent")
        title_line.pack(anchor="w")

        ctk.CTkLabel(
            title_line,
            text="Youtify",
            font=("Segoe UI", 22, "bold"),
            text_color=Colors.TEXT_PRIMARY,
        ).pack(side="left")

        ctk.CTkLabel(
            title_line,
            text="v1.0.6",
            font=("Segoe UI", 10, "bold"),
            text_color=Colors.TEXT_MUTED,
            fg_color=Colors.CARD_BG,
            corner_radius=6,
            padx=7,
            pady=2,
        ).pack(side="left", padx=(10, 0))

        ctk.CTkLabel(
            text_group,
            text="Descargador de audio y video de YouTube",
            font=("Segoe UI", 12),
            text_color=Colors.TEXT_SECONDARY,
        ).pack(anchor="w", pady=(1, 0))

    def _render_icon(self, parent, icon_path: Path):
        try:
            if icon_path.exists():
                img = Image.open(str(icon_path))
                img = img.convert("RGBA").resize((44, 44), Image.LANCZOS)
                self.icon_image = ctk.CTkImage(light_image=img, dark_image=img, size=(44, 44))
                ctk.CTkLabel(parent, image=self.icon_image, text="").pack(side="left")
        except Exception:
            pass
