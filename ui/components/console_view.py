import re
import customtkinter as ctk
from config.settings import MAX_LOG_BUFFER_LINES
from ui.theme import Colors

_ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


class ConsoleView(ctk.CTkFrame):
    """Consola moderna estilo terminal con buffer rotativo y limpieza rápida."""

    def __init__(self, parent):
        super().__init__(
            parent,
            fg_color=Colors.CONSOLE_BG,
            corner_radius=10,
            border_width=1,
            border_color=Colors.BORDER_SUBTLE,
        )
        self.pack(fill="x", padx=35, pady=(2, 14))
        self._line_count = 0

        # Barra de cabecera de la consola
        top_bar = ctk.CTkFrame(self, fg_color="transparent", height=24)
        top_bar.pack(fill="x", padx=10, pady=(6, 2))

        ctk.CTkLabel(
            top_bar,
            text="● REGISTRO DE DESCARGA",
            font=("Segoe UI", 10, "bold"),
            text_color=Colors.PRIMARY,
        ).pack(side="left")

        clear_btn = ctk.CTkButton(
            top_bar,
            text="Limpiar",
            width=60,
            height=20,
            font=("Segoe UI", 10),
            fg_color="transparent",
            hover_color=Colors.STATUS_IDLE_FG,
            text_color=Colors.TEXT_SUBTITLE,
            command=self.clear_logs,
        )
        clear_btn.pack(side="right")

        self.textbox = ctk.CTkTextbox(
            self,
            width=590,
            height=130,
            font=("Consolas", 11),
            fg_color="transparent",
            text_color=Colors.TEXT_CONSOLE,
            border_width=0,
        )
        self.textbox.pack(padx=8, pady=(0, 6))
        self.textbox.insert("0.1", "[*] Pega un enlace de YouTube y pulsa Descargar ahora.\n")
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
