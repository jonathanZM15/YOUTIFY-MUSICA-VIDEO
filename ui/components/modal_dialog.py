from typing import Optional
import customtkinter as ctk
from ui.theme import Colors


class ModalDialog(ctk.CTkToplevel):
    """Diálogo modal personalizado, moderno y minimalista con estética Obsidian."""

    def __init__(
        self,
        parent,
        title: str,
        message: str,
        dialog_type: str = "warning",  # 'warning', 'error', 'info', 'confirm'
        confirm_text: str = "Aceptar",
        cancel_text: str = "Cancelar",
    ):
        super().__init__(parent)
        self.result = False
        self.transient(parent)
        self.title(title)
        self.resizable(False, False)
        self.configure(fg_color=Colors.CARD_BG)

        # Dimensiones adaptativas y elegantes
        width = 440 if len(message) > 120 else 420
        height = 230 if len(message) > 120 else (200 if dialog_type == "confirm" else 180)

        # Centrar sobre la ventana padre
        parent.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width() // 2) - (width // 2)
        py = parent.winfo_rooty() + (parent.winfo_height() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{max(0, px)}+{max(0, py)}")

        # Iconografía y acentos según el tipo
        icons = {
            "warning": ("⚠️", "#eab308"),
            "error": ("❌", "#ef4444"),
            "info": ("ℹ️", "#0ea5e9"),
            "confirm": ("❓", "#f59e0b"),
        }
        icon_char, accent_color = icons.get(dialog_type, ("ℹ️", "#0ea5e9"))

        # Contenedor principal
        main_box = ctk.CTkFrame(self, fg_color="transparent")
        main_box.pack(fill="both", expand=True, padx=24, pady=20)

        # Fila superior: Icono + Título + Mensaje
        top_row = ctk.CTkFrame(main_box, fg_color="transparent")
        top_row.pack(fill="x", pady=(0, 16))

        icon_label = ctk.CTkLabel(
            top_row,
            text=icon_char,
            font=("Segoe UI", 26),
            width=36,
        )
        icon_label.pack(side="left", padx=(0, 14), anchor="n")

        msg_box = ctk.CTkFrame(top_row, fg_color="transparent")
        msg_box.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(
            msg_box,
            text=title,
            font=("Segoe UI", 13, "bold"),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
        ).pack(fill="x")

        ctk.CTkLabel(
            msg_box,
            text=message,
            font=("Segoe UI", 11),
            text_color=Colors.TEXT_SECONDARY,
            wraplength=310,
            justify="left",
            anchor="w",
        ).pack(fill="x", pady=(4, 0))

        # Botones de acción alineados a la derecha
        btn_row = ctk.CTkFrame(main_box, fg_color="transparent")
        btn_row.pack(fill="x", side="bottom")

        if dialog_type == "confirm":
            cancel_btn = ctk.CTkButton(
                btn_row,
                text=cancel_text,
                width=90,
                height=32,
                font=("Segoe UI", 11, "bold"),
                fg_color=Colors.BTN_SECONDARY_BG,
                text_color=Colors.BTN_SECONDARY_TEXT,
                hover_color=Colors.BTN_SECONDARY_HOVER,
                border_width=1,
                border_color=Colors.BTN_SECONDARY_BORDER,
                corner_radius=7,
                command=self._on_cancel,
            )
            cancel_btn.pack(side="right", padx=(8, 0))

        confirm_btn = ctk.CTkButton(
            btn_row,
            text=confirm_text,
            width=100,
            height=32,
            font=("Segoe UI", 11, "bold"),
            fg_color=Colors.PRIMARY,
            text_color="white",
            hover_color=Colors.PRIMARY_HOVER,
            corner_radius=7,
            command=self._on_confirm,
        )
        confirm_btn.pack(side="right")

        # Comportamiento modal estricto (bloquea la ventana padre hasta cerrar)
        self.grab_set()
        self.focus_force()

    def _on_confirm(self):
        self.result = True
        self.grab_release()
        self.destroy()

    def _on_cancel(self):
        self.result = False
        self.grab_release()
        self.destroy()

    @classmethod
    def show_warning(cls, parent, title: str, message: str) -> None:
        dialog = cls(parent, title=title, message=message, dialog_type="warning")
        parent.wait_window(dialog)

    @classmethod
    def show_error(cls, parent, title: str, message: str) -> None:
        dialog = cls(parent, title=title, message=message, dialog_type="error")
        parent.wait_window(dialog)

    @classmethod
    def show_info(cls, parent, title: str, message: str) -> None:
        dialog = cls(parent, title=title, message=message, dialog_type="info")
        parent.wait_window(dialog)

    @classmethod
    def ask_confirm(cls, parent, title: str, message: str) -> bool:
        dialog = cls(parent, title=title, message=message, dialog_type="confirm", confirm_text="Sí, salir", cancel_text="Cancelar")
        parent.wait_window(dialog)
        return dialog.result
