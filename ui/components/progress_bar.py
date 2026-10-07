import re
import customtkinter as ctk
from ui.theme import Colors

_ANSI_RE = re.compile(
    r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])|\x1b\[[0-9;]*[a-zA-Z]|\x1b\[[0-9;]*m"
)


def _clean_text(val: str) -> str:
    if not val:
        return ""
    return _ANSI_RE.sub("", str(val)).strip()


class ProgressBarWidget(ctk.CTkFrame):
    """Componente que agrupa la línea de progreso ultra-fina y el badge de estado minimalista."""

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.pack(fill="x", padx=36, pady=(12, 4))

        # Línea de progreso ultra-fina estilo moderno (4px)
        self.progress_bar = ctk.CTkProgressBar(
            self,
            height=4,
            corner_radius=2,
            progress_color=Colors.PRIMARY,
            fg_color=Colors.INPUT_BG,
        )
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", pady=(0, 8))

        # Estado textual sutil sin botones gigantes
        self.status_badge = ctk.CTkLabel(
            self,
            text="Listo para descargar",
            font=("Segoe UI", 12),
            text_color=Colors.TEXT_SECONDARY,
        )
        self.status_badge.pack(anchor="center")

    def set_progress(self, value: float) -> None:
        self.progress_bar.set(value)

    def set_active_download(self, current_item: int = 1, total_items: int = 1) -> None:
        self.progress_bar.configure(progress_color=Colors.PRIMARY)
        try:
            cur = int(current_item)
            tot = int(total_items)
            if tot > 1:
                badge_text = f"⚡ Descargando {cur} de {tot}"
            else:
                badge_text = "⚡ Descargando..."
        except (ValueError, TypeError):
            badge_text = "⚡ Descargando..."

        self.status_badge.configure(
            text=badge_text,
            text_color=Colors.STATUS_ACTIVE_TEXT,
        )

    def set_converting(self, current_item: int = 1, total_items: int = 1) -> None:
        self.set_active_download(current_item, total_items)

    def set_completed(self) -> None:
        self.progress_bar.configure(progress_color=Colors.PROGRESS_SUCCESS)
        self.progress_bar.set(1.0)
        self.status_badge.configure(
            text="✨ ¡Descarga completada con éxito!",
            text_color=Colors.STATUS_SUCCESS_TEXT,
        )

    def set_error(self, message: str = "Error en la descarga") -> None:
        self.progress_bar.configure(progress_color=Colors.PROGRESS_ERROR)
        self.status_badge.configure(
            text=f"❌ {message}",
            text_color=Colors.STATUS_ERROR_TEXT,
        )

    def reset_state(self) -> None:
        self.progress_bar.configure(progress_color=Colors.PRIMARY)
        self.progress_bar.set(0)
        self.status_badge.configure(
            text="Listo para descargar",
            text_color=Colors.TEXT_SECONDARY,
        )
