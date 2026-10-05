import io
import threading
import urllib.request
from typing import Optional
import customtkinter as ctk
from PIL import Image
from ui.theme import Colors


class PreviewCard(ctk.CTkFrame):
    """Tarjeta interactiva minimalista que muestra miniatura, título y canal del video."""

    def __init__(self, parent):
        super().__init__(
            parent,
            fg_color=Colors.CARD_BG,
            corner_radius=12,
            border_width=1,
            border_color=Colors.BORDER,
        )
        self._thumb_img = None
        self._build_ui()

    def _build_ui(self):
        self.inner = ctk.CTkFrame(self, fg_color="transparent")
        self.inner.pack(fill="x", padx=16, pady=10)

        # Miniatura con fondo sutil
        self.thumb_container = ctk.CTkFrame(
            self.inner,
            fg_color=Colors.INPUT_BG,
            corner_radius=8,
            width=96,
            height=54,
        )
        self.thumb_container.pack(side="left", padx=(0, 14))
        self.thumb_container.pack_propagate(False)

        self.thumb_label = ctk.CTkLabel(
            self.thumb_container,
            text="🎬",
            font=("Segoe UI", 18),
        )
        self.thumb_label.pack(expand=True, fill="both")

        # Info textual
        info_frame = ctk.CTkFrame(self.inner, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True)

        self.title_label = ctk.CTkLabel(
            info_frame,
            text="",
            font=("Segoe UI", 12, "bold"),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
            wraplength=440,
            justify="left",
        )
        self.title_label.pack(fill="x", pady=(2, 3))

        badges_row = ctk.CTkFrame(info_frame, fg_color="transparent")
        badges_row.pack(anchor="w")

        self.channel_badge = ctk.CTkLabel(
            badges_row,
            text="",
            font=("Segoe UI", 11),
            text_color=Colors.TEXT_SECONDARY,
        )
        self.channel_badge.pack(side="left", padx=(0, 10))

        self.duration_badge = ctk.CTkLabel(
            badges_row,
            text="",
            font=("Segoe UI", 10, "bold"),
            text_color=Colors.TEXT_BRAND,
            fg_color=Colors.INPUT_BG,
            corner_radius=5,
            padx=7,
            pady=1,
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
            self.pack(fill="x", padx=36, pady=(0, 10), after=after_widget)
        else:
            self.pack(fill="x", padx=36, pady=(0, 10))

    def _fetch_and_render_thumb(self, url: str):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = resp.read()
            raw_img = Image.open(io.BytesIO(data))
            raw_img = raw_img.convert("RGBA").resize((96, 54), Image.LANCZOS)
            self._thumb_img = ctk.CTkImage(light_image=raw_img, dark_image=raw_img, size=(96, 54))
            self.after(0, lambda: self.thumb_label.configure(image=self._thumb_img, text=""))
        except Exception:
            pass

    def hide_preview(self):
        self.pack_forget()
        self.title_label.configure(text="")
        self.channel_badge.configure(text="")
        self.duration_badge.configure(text="")
        self.thumb_label.configure(image=None, text="🎬")
