import customtkinter as ctk
from ui.theme import Colors


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

    def set_active_download(self, pct_str: str, speed_str: str) -> None:
        self.progress_bar.configure(progress_color=Colors.PRIMARY)
        self.status_badge.configure(
            text=f"⚡ Descargando {pct_str}  •  {speed_str}",
            text_color=Colors.STATUS_ACTIVE_TEXT,
        )

    def set_converting(self) -> None:
        self.status_badge.configure(
            text="🔄 Ensamblando y aplicando carátula ID3...",
            text_color=Colors.STATUS_CONVERT_TEXT,
        )

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
