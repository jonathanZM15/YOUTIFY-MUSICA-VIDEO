import io
import threading
import urllib.request
from urllib.parse import urlparse
from typing import Optional
import customtkinter as ctk
from PIL import Image
from ui.theme import Colors


class PreviewCard(ctk.CTkFrame):
    """Tarjeta interactiva minimalista que muestra miniatura, título y canal del video."""

    def __init__(self, parent, dispatch=None, compact=False):
        super().__init__(
            parent,
            fg_color=Colors.CARD_BG,
            corner_radius=12,
            border_width=1,
            border_color=Colors.BORDER,
        )
        self._thumb_img = None
        self.compact = compact
        self.thumb_size = (64, 40) if compact else (96, 54)
        self.dispatch = dispatch or (lambda fn: self.after(0, fn))
        self._request_id = 0
        self._build_ui()

    def _build_ui(self):
        self.inner = ctk.CTkFrame(self, fg_color="transparent")
        self.inner.pack(fill="x", padx=16, pady=10)

        # Miniatura con fondo sutil
        self.thumb_container = ctk.CTkFrame(
            self.inner,
            fg_color=Colors.INPUT_BG,
            corner_radius=8,
            width=self.thumb_size[0],
            height=self.thumb_size[1],
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
            wraplength=160 if self.compact else 440,
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
        if self.compact:
            self.channel_badge.pack_forget()
            self.duration_badge.pack_forget()
            self.channel_badge.pack(anchor="w")
            self.duration_badge.pack(anchor="w", pady=(3, 0))

    def show_preview(
        self,
        title: str,
        channel: str,
        duration: str,
        thumbnail_url: Optional[str] = None,
        after_widget: Optional[ctk.CTkBaseClass] = None,
    ):
        self._request_id += 1
        limit = 42 if self.compact else 65
        short_title = title if len(title) <= limit else title[:limit - 1] + "…"
        self.title_label.configure(text=short_title)
        self.channel_badge.configure(text=channel[:24] if self.compact else channel)
        self.duration_badge.configure(text=duration)

        if thumbnail_url:
            req_id = self._request_id
            threading.Thread(target=self._fetch_and_render_thumb, args=(thumbnail_url, req_id), daemon=True).start()

        if after_widget:
            self.pack(fill="x", pady=(0, 12), after=after_widget)
        else:
            self.pack(fill="x", pady=(0, 12))

    # Límite de tamaño para miniaturas (5 MB) para evitar consumo excesivo de memoria
    MAX_THUMB_BYTES = 5 * 1024 * 1024

    def _fetch_and_render_thumb(self, url: str, req_id: int):
        try:
            # Solo permitir URLs HTTPS para mitigar ataques SSRF a servicios internos
            if not self._valid_thumbnail(url):
                return
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                if not self._valid_thumbnail(resp.geturl()):
                    return
                data = resp.read(self.MAX_THUMB_BYTES + 1)
            if len(data) > self.MAX_THUMB_BYTES:
                return
            with Image.open(io.BytesIO(data)) as source:
                if source.width * source.height > 16_000_000:
                    return
                raw_img = source.convert("RGBA").resize(self.thumb_size, Image.Resampling.LANCZOS)

            def _apply_thumb():
                if req_id == self._request_id:
                    self._thumb_img = ctk.CTkImage(light_image=raw_img, dark_image=raw_img, size=self.thumb_size)
                    self.thumb_label.configure(image=self._thumb_img, text="")

            self.dispatch(_apply_thumb)
        except Exception:
            pass

    @staticmethod
    def _valid_thumbnail(url):
        parsed = urlparse(url)
        host = parsed.hostname or ""
        return parsed.scheme == "https" and not parsed.username and (
            host == "ytimg.com" or host.endswith(".ytimg.com") or host.endswith(".ggpht.com"))

    def hide_preview(self):
        self._request_id += 1
        self.pack_forget()
        self.title_label.configure(text="")
        self.channel_badge.configure(text="")
        self.duration_badge.configure(text="")
        self._thumb_img = None
        self.thumb_label.configure(image="", text="🎬")
