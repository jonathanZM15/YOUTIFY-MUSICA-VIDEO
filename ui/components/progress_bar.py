import customtkinter as ctk
from ui.theme import Colors


class ProgressBarWidget(ctk.CTkFrame):
    """Componente que agrupa la barra de progreso fluida y el pill badge de estado dinámico."""

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.pack(fill="x", padx=30, pady=(6, 4))

        # Barra de progreso con altura refinada y esquinas suaves
        self.progress_bar = ctk.CTkProgressBar(
            self,
            width=580,
            height=8,
            corner_radius=4,
            progress_color=Colors.PRIMARY,
            fg_color=Colors.SECONDARY,
        )
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", pady=(4, 6))

        # Badge pill con borde tenue para aspecto premium
        self.status_badge = ctk.CTkLabel(
            self,
            text="Listo para descargar",
            fg_color=Colors.STATUS_IDLE_FG,
            text_color=Colors.STATUS_IDLE_TEXT,
            font=("Segoe UI", 12, "bold"),
            corner_radius=12,
            padx=16,
            pady=5,
        )
        self.status_badge.pack(pady=(2, 4))

    def set_progress(self, value: float) -> None:
        self.progress_bar.set(value)

    def set_active_download(self, pct_str: str, speed_str: str) -> None:
        self.progress_bar.configure(progress_color=Colors.PRIMARY)
        self.status_badge.configure(
            text=f"⚡ Descargando {pct_str}  •  {speed_str}",
            text_color=Colors.STATUS_ACTIVE_TEXT,
            fg_color=Colors.STATUS_ACTIVE_FG,
        )

    def set_converting(self) -> None:
        self.status_badge.configure(
            text="🔄 Ensamblando y aplicando carátula ID3...",
            text_color=Colors.STATUS_CONVERT_TEXT,
            fg_color=Colors.STATUS_CONVERT_FG,
        )

    def set_completed(self) -> None:
        self.progress_bar.configure(progress_color=Colors.PROGRESS_SUCCESS)
        self.progress_bar.set(1.0)
        self.status_badge.configure(
            text="✨ ¡Descarga completada con éxito!",
            text_color=Colors.STATUS_SUCCESS_TEXT,
            fg_color=Colors.STATUS_SUCCESS_FG,
        )

    def set_error(self, message: str = "Error en la descarga") -> None:
        self.progress_bar.configure(progress_color=Colors.PROGRESS_ERROR)
        self.status_badge.configure(
            text=f"❌ {message}",
            text_color=Colors.STATUS_ERROR_TEXT,
            fg_color=Colors.STATUS_ERROR_FG,
        )

    def reset_state(self) -> None:
        self.progress_bar.configure(progress_color=Colors.PRIMARY)
        self.progress_bar.set(0)
        self.status_badge.configure(
            text="Listo para descargar",
            text_color=Colors.STATUS_IDLE_TEXT,
            fg_color=Colors.STATUS_IDLE_FG,
        )
