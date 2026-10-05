import io
import threading
import urllib.request
from typing import Optional
import customtkinter as ctk
from PIL import Image
from ui.theme import Colors


class PreviewCard(ctk.CTkFrame):
    """Tarjeta interactiva que muestra miniatura, título, canal y duración del video."""

    def __init__(self, parent):
        super().__init__(
            parent,
            fg_color=Colors.CARD_BG,
            corner_radius=12,
            border_width=1,
            border_color=Colors.BORDER_SUBTLE,
        )
        self._thumb_img = None
        self._build_ui()

    def _build_ui(self):
        # Contenedor interior
        self.inner = ctk.CTkFrame(self, fg_color="transparent")
        self.inner.pack(fill="x", padx=12, pady=8)

        # Miniatura (Placeholder por defecto)
        self.thumb_label = ctk.CTkLabel(
            self.inner,
            text="🎬",
            font=("Segoe UI", 24),
            width=90,
            height=54,
            corner_radius=8,
            fg_color=Colors.CONSOLE_BG,
        )
        self.thumb_label.pack(side="left", padx=(0, 12))

        # Información textual
        info_frame = ctk.CTkFrame(self.inner, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True)

        self.title_label = ctk.CTkLabel(
            info_frame,
            text="",
            font=("Segoe UI", 12, "bold"),
            text_color=Colors.TEXT_MAIN,
            anchor="w",
            wraplength=420,
            justify="left",
        )
        self.title_label.pack(fill="x")

        self.details_label = ctk.CTkLabel(
            info_frame,
            text="",
            font=("Segoe UI", 11),
            text_color=Colors.TEXT_MUTED,
            anchor="w",
        )
        self.details_label.pack(fill="x", pady=(2, 0))

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
        self.details_label.configure(text=f"👤 {channel}   •   ⏱️ {duration}")

        if thumbnail_url:
            threading.Thread(target=self._fetch_and_render_thumb, args=(thumbnail_url,), daemon=True).start()

        if after_widget:
            self.pack(fill="x", padx=35, pady=(0, 6), after=after_widget)
        else:
            self.pack(fill="x", padx=35, pady=(0, 6))

    def _fetch_and_render_thumb(self, url: str):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = resp.read()
            raw_img = Image.open(io.BytesIO(data))
            # Escalar a aspect ratio 16:9 miniatura (96x54)
            raw_img = raw_img.convert("RGBA").resize((96, 54), Image.LANCZOS)
            self._thumb_img = ctk.CTkImage(light_image=raw_img, dark_image=raw_img, size=(96, 54))
            self.after(0, lambda: self.thumb_label.configure(image=self._thumb_img, text=""))
        except Exception:
            pass

    def hide_preview(self):
        self.pack_forget()
        self.title_label.configure(text="")
        self.details_label.configure(text="")
        self.thumb_label.configure(image=None, text="🎬")
