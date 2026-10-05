import io
import threading
import urllib.request
from typing import Optional
import customtkinter as ctk
from PIL import Image
from ui.theme import Colors


class PreviewCard(ctk.CTkFrame):
    """Tarjeta interactiva elegante que muestra miniatura en alta calidad, título y duración."""

    def __init__(self, parent):
        super().__init__(
            parent,
            fg_color=Colors.CARD_BG,
            corner_radius=14,
            border_width=1,
            border_color=Colors.BORDER_CARD,
        )
        self._thumb_img = None
        self._build_ui()

    def _build_ui(self):
        # Contenedor interior con padding consistente
        self.inner = ctk.CTkFrame(self, fg_color="transparent")
        self.inner.pack(fill="x", padx=16, pady=10)

        # Miniatura (Placeholder por defecto con bordes redondeados y fondo sutil)
        self.thumb_container = ctk.CTkFrame(
            self.inner,
            fg_color=Colors.CONSOLE_BG,
            corner_radius=8,
            width=100,
            height=58,
        )
        self.thumb_container.pack(side="left", padx=(0, 14))
        self.thumb_container.pack_propagate(False)

        self.thumb_label = ctk.CTkLabel(
            self.thumb_container,
            text="🎬",
            font=("Segoe UI", 20),
        )
        self.thumb_label.pack(expand=True, fill="both")

        # Información textual (Título + Badges de canal y duración)
        info_frame = ctk.CTkFrame(self.inner, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True)

        self.title_label = ctk.CTkLabel(
            info_frame,
            text="",
            font=("Segoe UI", 12, "bold"),
            text_color=Colors.TEXT_TITLE,
            anchor="w",
            wraplength=430,
            justify="left",
        )
        self.title_label.pack(fill="x", pady=(1, 3))

        badges_row = ctk.CTkFrame(info_frame, fg_color="transparent")
        badges_row.pack(anchor="w")

        self.channel_badge = ctk.CTkLabel(
            badges_row,
            text="",
            font=("Segoe UI", 11),
            text_color=Colors.TEXT_MUTED,
        )
        self.channel_badge.pack(side="left", padx=(0, 12))

        self.duration_badge = ctk.CTkLabel(
            badges_row,
            text="",
            font=("Segoe UI", 11, "bold"),
            text_color=Colors.TEXT_BRAND,
            fg_color=Colors.SECONDARY,
            corner_radius=6,
            padx=8,
            pady=2,
        )
        self.duration_badge.pack(side="left")

    def show_preview(
        self,
        title: str,
        channel: str,
        duration: str,
        thumbnail_url: Optional[str] = None,
        after_widget: Optional[ctk.CTkBaseClass] = None,
    ):
        short_title = title if len(title) <= 65 else title[:62] + "..."
        self.title_label.configure(text=short_title)
        self.channel_badge.configure(text=f"👤 {channel}")
        self.duration_badge.configure(text=f"⏱️ {duration}")

        if thumbnail_url:
            threading.Thread(target=self._fetch_and_render_thumb, args=(thumbnail_url,), daemon=True).start()

        if after_widget:
            self.pack(fill="x", padx=30, pady=(0, 6), after=after_widget)
        else:
            self.pack(fill="x", padx=30, pady=(0, 6))

    def _fetch_and_render_thumb(self, url: str):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = resp.read()
            raw_img = Image.open(io.BytesIO(data))
            raw_img = raw_img.convert("RGBA").resize((100, 58), Image.LANCZOS)
            self._thumb_img = ctk.CTkImage(light_image=raw_img, dark_image=raw_img, size=(100, 58))
            self.after(0, lambda: self.thumb_label.configure(image=self._thumb_img, text=""))
        except Exception:
            pass

    def hide_preview(self):
        self.pack_forget()
        self.title_label.configure(text="")
        self.channel_badge.configure(text="")
        self.duration_badge.configure(text="")
        self.thumb_label.configure(image=None, text="🎬")
