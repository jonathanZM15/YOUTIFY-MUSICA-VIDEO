import re
import customtkinter as ctk
from config.settings import MAX_LOG_BUFFER_LINES
from ui.theme import Colors

_ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


class ConsoleView(ctk.CTkFrame):
    """Consola moderna estilo terminal macOS/VS Code con ventana de terminal integrada."""

    def __init__(self, parent):
        super().__init__(
            parent,
            fg_color=Colors.CONSOLE_CONTAINER,
            corner_radius=14,
            border_width=1,
            border_color=Colors.BORDER_CARD,
        )
        self.pack(fill="x", padx=30, pady=(4, 16))
        self._line_count = 0

        # Barra superior de la terminal
        top_bar = ctk.CTkFrame(self, fg_color="transparent", height=28)
        top_bar.pack(fill="x", padx=16, pady=(10, 4))

        # Indicador de estado (puntos de terminal de colores estilo Mac/Terminal)
        dots_box = ctk.CTkFrame(top_bar, fg_color="transparent")
        dots_box.pack(side="left")

        ctk.CTkLabel(
            dots_box,
            text="●",
            font=("Segoe UI", 12),
            text_color="#ef4444",
        ).pack(side="left", padx=(0, 4))
        ctk.CTkLabel(
            dots_box,
            text="●",
            font=("Segoe UI", 12),
            text_color="#eab308",
        ).pack(side="left", padx=(0, 4))
        ctk.CTkLabel(
            dots_box,
            text="●",
            font=("Segoe UI", 12),
            text_color="#22c55e",
        ).pack(side="left", padx=(0, 10))

        ctk.CTkLabel(
            dots_box,
            text="TERMINAL DE REGISTRO",
            font=("Segoe UI", 10, "bold"),
            text_color=Colors.TEXT_MUTED,
        ).pack(side="left")

        clear_btn = ctk.CTkButton(
            top_bar,
            text="Limpiar consola",
            width=85,
            height=22,
            font=("Segoe UI", 10, "bold"),
            fg_color=Colors.SECONDARY,
            hover_color=Colors.SECONDARY_HOVER,
            text_color=Colors.TEXT_MUTED,
            corner_radius=6,
            command=self.clear_logs,
        )
        clear_btn.pack(side="right")

        # Área de texto terminal
        text_wrapper = ctk.CTkFrame(self, fg_color=Colors.CONSOLE_BG, corner_radius=10)
        text_wrapper.pack(fill="x", padx=12, pady=(0, 10))

        self.textbox = ctk.CTkTextbox(
            text_wrapper,
            height=120,
            font=("Consolas", 11),
            fg_color="transparent",
            text_color=Colors.TEXT_CONSOLE,
            border_width=0,
            wrap="word",
        )
        self.textbox.pack(fill="both", expand=True, padx=8, pady=4)
        self.textbox.insert("0.1", "[*] Sistema listo. Pega un enlace de YouTube para comenzar.\n")
        self.textbox.configure(state="disabled")

    def append_log(self, message: str) -> None:
        clean_msg = _ANSI_RE.sub("", message).strip()
        if not clean_msg:
            return

        self.textbox.configure(state="normal")
        self._line_count += 1
        if self._line_count > MAX_LOG_BUFFER_LINES:
            self.textbox.delete("1.0", "2.0")
            self._line_count -= 1

        self.textbox.insert("end", clean_msg + "\n")
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def clear_logs(self) -> None:
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.configure(state="disabled")
        self._line_count = 0
