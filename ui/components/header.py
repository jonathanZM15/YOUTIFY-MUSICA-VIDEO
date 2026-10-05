from pathlib import Path
import customtkinter as ctk
from PIL import Image
from ui.theme import Colors


class Header(ctk.CTkFrame):
    """Componente de cabecera con branding pulido, logo nítido y línea de acento."""

    def __init__(self, parent, icon_path: Path):
        super().__init__(
            parent,
            fg_color=Colors.HEADER_BG,
            corner_radius=0,
            border_width=0,
        )
        self.pack(fill="x")

        # Contenedor centralizado horizontalmente
        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="x", padx=30, pady=(16, 12))

        # Fila horizontal: Logo a la izquierda, título y subtítulo agrupados
        brand_row = ctk.CTkFrame(inner, fg_color="transparent")
        brand_row.pack(anchor="center")

        # Contenedor del icono con fondo sutil circular/redondeado
        self.icon_badge = ctk.CTkFrame(
            brand_row,
            fg_color=("transparent", "transparent"),
            corner_radius=12,
            width=50,
            height=50,
        )
        self.icon_badge.pack(side="left", padx=(0, 14))

        self._render_icon(self.icon_badge, icon_path)

        # Textos alineados verticalmente
        titles_box = ctk.CTkFrame(brand_row, fg_color="transparent")
        titles_box.pack(side="left")

        title_row = ctk.CTkFrame(titles_box, fg_color="transparent")
        title_row.pack(anchor="w")

        ctk.CTkLabel(
            title_row,
            text="YOUTIFY",
            font=("Segoe UI", 24, "bold"),
            text_color=Colors.TEXT_BRAND,
        ).pack(side="left")

        # Badge de versión prolijo
        ctk.CTkLabel(
            title_row,
            text="v1.0.6",
            font=("Segoe UI", 10, "bold"),
            text_color=Colors.TEXT_MUTED,
            fg_color=Colors.SECONDARY,
            corner_radius=6,
            padx=7,
            pady=2,
        ).pack(side="left", padx=(10, 0))

        ctk.CTkLabel(
            titles_box,
            text="Descarga música y videos en alta fidelidad de YouTube",
            font=("Segoe UI", 12),
            text_color=Colors.TEXT_MUTED,
        ).pack(anchor="w", pady=(2, 0))

        # Línea divisoria inferior muy sutil
        ctk.CTkFrame(
            self,
            height=1,
            fg_color=Colors.HEADER_BORDER,
            corner_radius=0,
        ).pack(fill="x", side="bottom")

    def _render_icon(self, parent, icon_path: Path):
        try:
            if icon_path.exists():
                img = Image.open(str(icon_path))
                img = img.convert("RGBA").resize((48, 48), Image.LANCZOS)
                self.icon_image = ctk.CTkImage(light_image=img, dark_image=img, size=(48, 48))
                ctk.CTkLabel(parent, image=self.icon_image, text="").pack(anchor="center")
        except Exception:
            pass
