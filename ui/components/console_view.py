import customtkinter as ctk
import tkinter as tk
from config.settings import MAX_LOG_BUFFER_LINES
from core.downloader import ANSI_ESCAPE_RE as _ANSI_RE
from ui.theme import Colors


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
        self.pack(fill="both", expand=True, padx=6, pady=(4, 8))
        self._line_count = 1

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
        area = ctk.CTkFrame(self, fg_color=Colors.CONSOLE_BG, corner_radius=8)
        area.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        area.grid_columnconfigure(0, weight=1)
        area.grid_rowconfigure(0, weight=1)
        # Tk's text reports scroll changes through a callback. CTkTextbox polls
        # its scrollbars every 200 ms, including while this tab is hidden.
        self.textbox = tk.Text(area, height=6, width=1, wrap="word", borderwidth=0,
            highlightthickness=0, font=self._apply_font_scaling(("Consolas",11)),
            padx=0, pady=0)
        self.textbox.grid(row=0,column=0,sticky="nsew",padx=(8,0),pady=8)
        scrollbar = ctk.CTkScrollbar(area, command=self.textbox.yview,
            fg_color=Colors.CONSOLE_BG, button_color=Colors.BORDER)
        scrollbar.grid(row=0,column=1,sticky="ns",padx=(2,4),pady=8)
        self.textbox.configure(yscrollcommand=scrollbar.set)
        self._style_text()
        self.textbox.insert("1.0", "[*] Listo para descargar. Pega un enlace de YouTube arriba.\n")
        self.textbox.configure(state="disabled")

    def append_log(self, message: str) -> None:
        self.append_logs([message])

    def append_logs(self, messages) -> None:
        clean = [_ANSI_RE.sub("", str(message)).strip() for message in messages]
        clean = [message for message in clean if message]
        if not clean: return
        text = "\n".join(clean) + "\n"
        self.textbox.configure(state="normal")
        self.textbox.insert("end", text)
        self._line_count += text.count("\n")
        excess = self._line_count - MAX_LOG_BUFFER_LINES
        if excess > 0:
            self.textbox.delete("1.0", f"{excess+1}.0")
            self._line_count -= excess
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def _style_text(self):
        self.textbox.configure(background=self._apply_appearance_mode(Colors.CONSOLE_BG),
            foreground=self._apply_appearance_mode(Colors.TEXT_CONSOLE),
            selectbackground=self._apply_appearance_mode(Colors.PRIMARY))

    def _set_appearance_mode(self, mode):
        super()._set_appearance_mode(mode)
        if hasattr(self, 'textbox'): self._style_text()

    def _set_scaling(self, *args):
        super()._set_scaling(*args)
        if hasattr(self, 'textbox'):
            self.textbox.configure(font=self._apply_font_scaling(("Consolas",11)))

    def clear_logs(self) -> None:
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.configure(state="disabled")
        self._line_count = 0
