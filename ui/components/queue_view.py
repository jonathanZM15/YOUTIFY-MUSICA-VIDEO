from pathlib import Path
import os
import customtkinter as ctk
from ui.theme import Colors

STATUS = {
    "pending": ("En espera", Colors.TEXT_MUTED),
    "resolving": ("Leyendo playlist", Colors.TEXT_BRAND),
    "downloading": ("Descargando", Colors.TEXT_BRAND),
    "converting": ("Guardando", Colors.STATUS_CONVERT_TEXT),
    "completed": ("Guardado", Colors.SUCCESS),
    "failed": ("Error", Colors.ERROR),
    "cancelled": ("Cancelado", Colors.TEXT_MUTED),
}


class QueueView(ctk.CTkFrame):
    def __init__(self, parent, on_cancel, on_retry, on_open):
        super().__init__(parent, fg_color=Colors.CARD_BG, corner_radius=10)
        self.pack(fill="both", expand=True)
        self.list = ctk.CTkScrollableFrame(self, fg_color=Colors.CARD_BG, height=160)
        self.list.pack(fill="both", expand=True)
        self.list.grid_columnconfigure(0, weight=1)
        self.actions = (on_cancel, on_retry, on_open)
        self.rows = {}
        self.page = 0
        self._jobs = []
        self._active = None
        pager = ctk.CTkFrame(self, fg_color="transparent")
        pager.pack(fill="x", padx=8, pady=(4, 0))
        self.page_label = ctk.CTkLabel(pager, text="", font=("Segoe UI", 10), text_color=Colors.TEXT_MUTED)
        self.page_label.pack(side="left")
        self.next_btn = ctk.CTkButton(pager, text="Siguiente →", command=lambda: self._turn_page(1), width=90, height=24,
            font=("Segoe UI", 10), fg_color="transparent", text_color=Colors.TEXT_SECONDARY, hover_color=Colors.CARD_HOVER)
        self.next_btn.pack(side="right")
        self.prev_btn = ctk.CTkButton(pager, text="← Anterior", command=lambda: self._turn_page(-1), width=90, height=24,
            font=("Segoe UI", 10), fg_color="transparent", text_color=Colors.TEXT_SECONDARY, hover_color=Colors.CARD_HOVER)
        self.prev_btn.pack(side="right")
        self.empty = ctk.CTkFrame(self.list, fg_color="transparent")
        ctk.CTkLabel(self.empty, text="↓", width=54, height=54, corner_radius=27,
            fg_color=Colors.INPUT_BG, text_color=Colors.TEXT_BRAND, font=("Segoe UI", 30)).pack(pady=(24, 12))
        ctk.CTkLabel(self.empty, text="Tu cola está vacía", font=("Segoe UI", 14, "bold"),
            text_color=Colors.TEXT_PRIMARY).pack()
        ctk.CTkLabel(self.empty, text="Pega un enlace y elige cómo quieres guardarlo.", wraplength=280,
            font=("Segoe UI", 11), text_color=Colors.TEXT_MUTED).pack(pady=(3, 16))
        self.empty.grid(row=0, column=0, sticky="ew")

    def _turn_page(self, offset):
        self.page += offset
        self.render(self._jobs)
        self.list._parent_canvas.yview_moveto(0)

    def render(self, jobs):
        self._jobs = jobs
        self.list._scrollbar.configure(button_color=Colors.BORDER if jobs else Colors.CARD_BG)
        active = next((i for i, job in enumerate(jobs) if job["status"] in {"downloading", "converting"}), None)
        if active is not None and jobs[active]["id"] != self._active:
            self.page = active // 25
            self._active = jobs[active]["id"]
        pages = max(1, (len(jobs) + 24) // 25)
        self.page = max(0, min(self.page, pages - 1))
        self.page_label.configure(text=f"Página {self.page + 1} de {pages}" if jobs else "")
        self.prev_btn.configure(state="normal" if self.page > 0 else "disabled")
        self.next_btn.configure(state="normal" if self.page + 1 < pages else "disabled")
        jobs = jobs[self.page * 25:(self.page + 1) * 25]
        if jobs:
            self.empty.grid_remove()
        else:
            self.empty.grid()
        ids = {job["id"] for job in jobs}
        for key in list(self.rows):
            if key not in ids:
                self.rows.pop(key)["frame"].destroy()
        for index, job in enumerate(jobs):
            key = job["id"]
            if key not in self.rows:
                frame = ctk.CTkFrame(self.list, fg_color=Colors.INPUT_BG, corner_radius=9)
                frame.grid_columnconfigure(1, weight=1)
                badge = ctk.CTkLabel(frame, text="MP3" if job["format_type"].startswith("MP3") else "MP4",
                    width=44, height=40, corner_radius=7, fg_color=Colors.BTN_SECONDARY_BG,
                    text_color=Colors.TEXT_BRAND, font=("Segoe UI", 10, "bold"))
                badge.grid(row=0, column=0, rowspan=2, padx=12, pady=12)
                title = ctk.CTkLabel(frame, text="", width=1, anchor="w", font=("Segoe UI", 12, "bold"), text_color=Colors.TEXT_PRIMARY)
                title.grid(row=0, column=1, sticky="ew", pady=(9, 0))
                detail = ctk.CTkLabel(frame, text="", width=1, anchor="w", font=("Segoe UI", 10), text_color=Colors.TEXT_MUTED)
                detail.grid(row=1, column=1, sticky="ew", pady=(0, 9))
                status = ctk.CTkLabel(frame, text="", width=108, font=("Segoe UI", 11))
                status.grid(row=0, column=2, rowspan=2, padx=10)
                button = ctk.CTkButton(frame, text="", width=86, height=28, fg_color=Colors.BTN_SECONDARY_BG,
                    hover_color=Colors.BTN_SECONDARY_HOVER, text_color=Colors.BTN_SECONDARY_TEXT, font=("Segoe UI", 10))
                button.grid(row=0, column=3, rowspan=2, padx=(0, 12))
                self.rows[key] = dict(frame=frame, title=title, detail=detail, status=status, button=button)
            row = self.rows[key]
            row["frame"].grid(row=index + 1, column=0, sticky="ew", pady=(0, 6), padx=2)
            title = job["title"]
            # Truncation keeps a very long remote title from stretching the window.
            row["title"].configure(text=title[:64] + ("…" if len(title) > 64 else ""))
            detail = job["error"].splitlines()[0] if job["error"] else f'{job["quality"]}   ·   {Path(job["destination"]).name}'
            row["detail"].configure(text=detail[:90], text_color=Colors.ERROR if job["error"] else Colors.TEXT_MUTED)
            label, color = STATUS.get(job["status"], STATUS["pending"])
            row["status"].configure(text=label, text_color=color)
            if job["status"] == "completed":
                text, action = "Abrir", lambda j=job: self.actions[2](j)
            elif job["status"] in {"failed", "cancelled"}:
                text, action = "Reintentar", lambda jid=key: self.actions[1](jid)
            else:
                text, action = "Cancelar", lambda jid=key: self.actions[0](jid)
            row["button"].configure(text=text, command=action)
