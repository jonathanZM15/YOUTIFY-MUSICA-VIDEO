import re
import customtkinter as ctk
from config.settings import MAX_LOG_BUFFER_LINES
from ui.theme import Colors

_ANSI_RE = re.compile(
    r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])|\x1b\[[0-9;]*[a-zA-Z]|\x1b\[[0-9;]*m"
)


class ConsoleView(ctk.CTkFrame):
    """Consola moderna minimalista con micro-header y caja de texto limpia."""

    def __init__(self, parent):
        super().__init__(
            parent,
            fg_color=Colors.CARD_BG,
            corner_radius=12,
            border_width=1,
            border_color=Colors.BORDER,
        )
        self.pack(fill="x", padx=36, pady=(6, 20))
        self._line_count = 0

        # Barra superior sutil
        top_bar = ctk.CTkFrame(self, fg_color="transparent", height=24)
        top_bar.pack(fill="x", padx=14, pady=(10, 4))

        ctk.CTkLabel(
            top_bar,
            text="REGISTRO DE ACTIVIDAD",
            font=("Segoe UI", 10, "bold"),
            text_color=Colors.TEXT_MUTED,
        ).pack(side="left")

        clear_btn = ctk.CTkButton(
            top_bar,
            text="Limpiar",
            width=60,
            height=20,
            font=("Segoe UI", 10),
            fg_color="transparent",
            hover_color=Colors.INPUT_BG,
            text_color=Colors.TEXT_SECONDARY,
            corner_radius=5,
            command=self.clear_logs,
        )
        clear_btn.pack(side="right")

        # Área de texto
        self.textbox = ctk.CTkTextbox(
            self,
            height=110,
            font=("Consolas", 11),
            fg_color=Colors.CONSOLE_BG,
            text_color=Colors.TEXT_CONSOLE,
            border_width=0,
            corner_radius=8,
            wrap="word",
        )
        self.textbox.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.textbox.insert("0.1", "[*] Listo para descargar. Pega un enlace de YouTube arriba.\n")
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
