import webbrowser
import customtkinter as ctk

from config.settings import APP_VERSION
from core.updater import ReleaseInfo, Updater
from ui.theme import Colors


class UpdateDialog(ctk.CTkToplevel):
    """Ventana modal minimalista y moderna para notificar nuevas versiones de software."""

    def __init__(self, parent, release_info: ReleaseInfo):
        super().__init__(parent)
        self.parent = parent
        self.release_info = release_info

        self.transient(parent)
        self.title("Actualización disponible")
        self.resizable(False, False)
        self.configure(fg_color=Colors.CARD_BG)

        # Dimensiones de la ventana modal
        width = 460
        height = 290

        # Centrar relativo a la ventana principal
        parent.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width() // 2) - (width // 2)
        py = parent.winfo_rooty() + (parent.winfo_height() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{max(0, px)}+{max(0, py)}")

        # Contenedor principal
        main_box = ctk.CTkFrame(self, fg_color="transparent")
        main_box.pack(fill="both", expand=True, padx=24, pady=20)

        # ── Cabecera: Icono e Identificación de Versión ──
        header_row = ctk.CTkFrame(main_box, fg_color="transparent")
        header_row.pack(fill="x", pady=(0, 14))

        icon_label = ctk.CTkLabel(
            header_row,
            text="🚀",
            font=("Segoe UI", 28),
            width=40,
        )
        icon_label.pack(side="left", padx=(0, 12), anchor="n")

        title_box = ctk.CTkFrame(header_row, fg_color="transparent")
        title_box.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(
            title_box,
            text="¡Nueva actualización disponible!",
            font=("Segoe UI", 14, "bold"),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
        ).pack(fill="x")

        ver_text = f"Versión v{release_info.version} disponible (tu versión actual es v{APP_VERSION})"
        ctk.CTkLabel(
            title_box,
            text=ver_text,
            font=("Segoe UI", 11),
            text_color=Colors.TEXT_BRAND,
            anchor="w",
        ).pack(fill="x", pady=(2, 0))

        # ── Cuadro de notas / changelog ──
        notes_frame = ctk.CTkFrame(
            main_box,
            fg_color=Colors.INPUT_BG,
            corner_radius=8,
            border_width=1,
            border_color=Colors.BORDER_INPUT,
        )
        notes_frame.pack(fill="both", expand=True, pady=(0, 18))

        ctk.CTkLabel(
            notes_frame,
            text=release_info.release_notes or "Mejoras de rendimiento y compatibilidad con YouTube.",
            font=("Segoe UI", 11),
            text_color=Colors.TEXT_SECONDARY,
            wraplength=380,
            justify="left",
            anchor="nw",
        ).pack(fill="both", expand=True, padx=14, pady=12)

        # ── Fila de botones de decisión ──
        btn_row = ctk.CTkFrame(main_box, fg_color="transparent")
        btn_row.pack(fill="x", side="bottom")

        # Botón 3: No por ahora / Cerrar
        cancel_btn = ctk.CTkButton(
            btn_row,
            text="No por ahora",
            width=90,
            height=34,
            font=("Segoe UI", 11),
            fg_color="transparent",
            text_color=Colors.TEXT_MUTED,
            hover_color=Colors.CARD_HOVER,
            corner_radius=7,
            command=self._on_no,
        )
        cancel_btn.pack(side="left")

        # Botón 2: Recordar más tarde (24h)
        later_btn = ctk.CTkButton(
            btn_row,
            text="Recordar más tarde",
            width=135,
            height=34,
            font=("Segoe UI", 11, "bold"),
            fg_color=Colors.BTN_SECONDARY_BG,
            text_color=Colors.BTN_SECONDARY_TEXT,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            border_width=1,
            border_color=Colors.BTN_SECONDARY_BORDER,
            corner_radius=7,
            command=self._on_remind_later,
        )
        later_btn.pack(side="right", padx=(8, 0))

        # Botón 1: Actualizar ahora
        update_btn = ctk.CTkButton(
            btn_row,
            text="Actualizar ahora",
            width=125,
            height=34,
            font=("Segoe UI", 11, "bold"),
            fg_color=Colors.PRIMARY,
            text_color="white",
            hover_color=Colors.PRIMARY_HOVER,
            corner_radius=7,
            command=self._on_update_now,
        )
        update_btn.pack(side="right")

        # Configurar modalidad
        self.grab_set()
        self.focus_force()

    def _on_update_now(self):
        """Abre la descarga directa o release de GitHub en el navegador del usuario de forma segura."""
        target_url = self.release_info.download_url or self.release_info.html_url
        if target_url and target_url.startswith("https://"):
            webbrowser.open(target_url)
        self.grab_release()
        self.destroy()

    def _on_remind_later(self):
        """Pospone la notificación para recordar en 24 horas."""
        Updater.postpone_update(self.release_info.tag_name, hours=24)
        self.grab_release()
        self.destroy()

    def _on_no(self):
        """Cierra el diálogo para la sesión actual."""
        self.grab_release()
        self.destroy()
