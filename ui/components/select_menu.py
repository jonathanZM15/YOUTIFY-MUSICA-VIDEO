"""Read-only selection with a rounded popup, independent of native Tk menus."""
import sys
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageDraw
from ui.theme import Colors


def _chevron(up=False):
    def draw(color):
        image = Image.new("RGBA", (48, 32))
        points = [(8, 10), (24, 24), (40, 10)]
        if up: points = [(x, 32-y) for x, y in points]
        ImageDraw.Draw(image).line(points, fill=color, width=6, joint="curve")
        return image
    return ctk.CTkImage(light_image=draw(Colors.TEXT_SECONDARY[0]),
        dark_image=draw(Colors.TEXT_SECONDARY[1]), size=(12, 8))


class _SelectPopup(tk.Toplevel):
    # CTk's DPI tracker also visits the native window hosting its child widgets.
    # Dismiss after that iteration, so its registry is never mutated mid-loop.
    def block_update_dimensions_event(self):
        pass

    def unblock_update_dimensions_event(self):
        owner = self.master
        if owner._dpi_close is None:
            owner._dpi_close = owner.after_idle(owner._close_after_dpi)


class SelectMenu(ctk.CTkFrame):
    def __init__(self, master, values, command=None, width=138, height=36,
                 font=("Segoe UI", 12), fg_color=Colors.INPUT_BG, text_color=Colors.TEXT_PRIMARY):
        self._values = list(values)
        self._command = command
        self._value = self._values[0] if self._values else ""
        self._state = "normal"
        self._popup = None
        self._rows = []
        self._root_binding = None
        self._focus_check = None
        self._dpi_close = None
        self._focused = self._hovered = False
        self._base_color = fg_color
        super().__init__(master, width=width, height=height, corner_radius=9,
            border_width=1, border_color=Colors.BORDER_INPUT, fg_color=fg_color, cursor="hand2")
        self.grid_propagate(False)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._down_image, self._up_image = _chevron(), _chevron(True)
        self._label = ctk.CTkLabel(self, text=self._value, width=1, height=20,
            anchor="w", font=font, text_color=text_color, cursor="hand2")
        self._label.grid(row=0, column=0, sticky="ew", padx=(12, 2), pady=2)
        self._arrow = ctk.CTkLabel(self, text="", width=20, height=20,
            image=self._down_image, cursor="hand2")
        self._arrow.grid(row=0, column=1, padx=(0, 9), pady=2)
        self._canvas.configure(takefocus=1)
        for widget in (self, self._label, self._arrow):
            widget.bind("<Button-1>", self._open_key, add="+")
            widget.bind("<Enter>", lambda event:self._hover(True), add="+")
            widget.bind("<Leave>", self._leave, add="+")
        self.bind("<FocusIn>", lambda event:self._focus(True), add="+")
        self.bind("<FocusOut>", lambda event:self._focus(False), add="+")
        for key in ("<space>", "<Return>", "<Down>", "<Up>", "<F4>"):
            self.bind(key, self._open_key, add="+")

    def get(self):
        return self._value

    def set(self, value):
        if value not in self._values:
            raise ValueError(f"Unknown selection: {value}")
        self._value = value
        self._label.configure(text=value)

    def cget(self, attribute_name):
        if attribute_name == "values": return list(self._values)
        if attribute_name == "command": return self._command
        if attribute_name == "state": return self._state
        return super().cget(attribute_name)

    def configure(self, **kwargs):
        if "values" in kwargs:
            self.close()
            self._values = list(kwargs.pop("values"))
            if self._value not in self._values:
                self._value = self._values[0] if self._values else ""
                self._label.configure(text=self._value)
        if "command" in kwargs: self._command = kwargs.pop("command")
        if "state" in kwargs:
            self._state = kwargs.pop("state")
            if self._state == "disabled": self.close()
            self._canvas.configure(takefocus=int(self._state != "disabled"))
            self._label.configure(text_color=Colors.TEXT_MUTED if self._state == "disabled" else Colors.TEXT_PRIMARY)
        super().configure(**kwargs)

    def focus_set(self):
        self._canvas.focus_set()

    def _focus(self, value):
        self._focused = value
        self._paint()

    def _hover(self, value):
        self._hovered = value
        self._paint()

    def _leave(self, event):
        x, y = self.winfo_pointerx(), self.winfo_pointery()
        self._hover(self.winfo_rootx() <= x < self.winfo_rootx()+self.winfo_width()
            and self.winfo_rooty() <= y < self.winfo_rooty()+self.winfo_height())

    def _paint(self):
        active = self._focused or self._popup is not None
        super().configure(border_color=Colors.BORDER_FOCUS if active else Colors.BORDER_INPUT,
            fg_color=Colors.CARD_HOVER if self._hovered and self._state != "disabled" else self._base_color)

    def _open_key(self, event):
        self.open()
        return "break"

    def _work_area(self):
        fallback = (0, 0, self.winfo_screenwidth(), self.winfo_screenheight())
        if sys.platform != "win32": return fallback
        import ctypes
        from ctypes import wintypes
        class MonitorInfo(ctypes.Structure):
            _fields_ = [("size", wintypes.DWORD), ("monitor", wintypes.RECT),
                ("work", wintypes.RECT), ("flags", wintypes.DWORD)]
        user = ctypes.WinDLL("user32", use_last_error=True)
        user.MonitorFromPoint.argtypes, user.MonitorFromPoint.restype = [wintypes.POINT, wintypes.DWORD], wintypes.HANDLE
        user.GetMonitorInfoW.argtypes, user.GetMonitorInfoW.restype = [wintypes.HANDLE, ctypes.POINTER(MonitorInfo)], wintypes.BOOL
        monitor = user.MonitorFromPoint(wintypes.POINT(self.winfo_rootx(), self.winfo_rooty()), 2)
        info = MonitorInfo(size=ctypes.sizeof(MonitorInfo))
        if not user.GetMonitorInfoW(monitor, ctypes.byref(info)): return fallback
        return info.work.left, info.work.top, info.work.right, info.work.bottom

    def open(self):
        if self._popup is not None:
            self.close()
            return
        if self._state == "disabled" or not self._values or not self.winfo_ismapped(): return
        root = self.winfo_toplevel()
        if root.grab_current() is not None: return
        self.focus_set()
        # A plain borderless Toplevel avoids CTkToplevel's global mouse bindings
        # and delayed title-bar callbacks, which are unnecessary for a popup.
        popup = self._popup = _SelectPopup(self, borderwidth=0, highlightthickness=0)
        popup.withdraw()
        popup.overrideredirect(True)
        popup.transient(root)
        transparent = "#010203"
        popup.configure(bg=transparent)
        try: popup.attributes("-transparentcolor", transparent)
        except tk.TclError: popup.configure(bg=self._apply_appearance_mode(Colors.APP_BG))
        popup.geometry(f"+{self.winfo_rootx()}+{self.winfo_rooty()}")
        popup.update_idletasks()
        panel = ctk.CTkFrame(popup, corner_radius=12, border_width=1,
            border_color=Colors.BORDER, fg_color=Colors.CARD_BG)
        panel.pack(fill="both", expand=True)
        self._rows = []
        for index, value in enumerate(self._values):
            selected = value == self._value
            row = ctk.CTkFrame(panel,
                width=max(90, self._reverse_widget_scaling(self.winfo_width())-12), height=32,
                corner_radius=7, border_width=0, cursor="hand2",
                fg_color=Colors.STATUS_ACTIVE_FG if selected else "transparent")
            row.pack(fill="x", padx=6, pady=(6 if index == 0 else 1, 6 if index == len(self._values)-1 else 1))
            row.pack_propagate(False)
            label = ctk.CTkLabel(row, text=("✓   " if selected else "     ")+value, anchor="w",
                height=20, font=("Segoe UI", 12), cursor="hand2",
                text_color=Colors.TEXT_BRAND if selected else Colors.TEXT_PRIMARY)
            label.pack(fill="both", expand=True, padx=8)
            for widget in (row, label):
                widget.bind("<Enter>", lambda event,i=index:self._highlight(i), add="+")
                widget.bind("<ButtonPress-1>", lambda event:"break", add="+")
                widget.bind("<ButtonRelease-1>", lambda event,i=index:self._release_row(event,i), add="+")
            self._rows.append(row)
        self._active_index = self._values.index(self._value)
        popup.update_idletasks()
        width = max(self.winfo_width(), popup.winfo_reqwidth())
        height = popup.winfo_reqheight()
        left, top, right, bottom = self._work_area()
        gap = round(self._apply_widget_scaling(6))
        x = max(left, min(self.winfo_rootx(), right-width))
        y = self.winfo_rooty()+self.winfo_height()+gap
        if y+height > bottom: y = self.winfo_rooty()-height-gap
        y = max(top, min(y, bottom-height))
        popup.geometry(f"{width}x{height}+{x}+{y}")
        popup.bind("<Escape>", lambda event:self._dismiss_key(), add="+")
        popup.bind("<Down>", lambda event:self._move(1), add="+")
        popup.bind("<Up>", lambda event:self._move(-1), add="+")
        popup.bind("<Home>", lambda event:self._highlight(0), add="+")
        popup.bind("<End>", lambda event:self._highlight(len(self._values)-1), add="+")
        for key in ("<Return>", "<space>"):
            popup.bind(key, lambda event:self._select(self._active_index), add="+")
        popup.bind("<Tab>", lambda event:self._tab(False), add="+")
        popup.bind("<Shift-Tab>", lambda event:self._tab(True), add="+")
        popup.bind("<ButtonPress-1>", self._outside_click, add="+")
        popup.bind("<FocusOut>", self._defer_focus_check, add="+")
        self._root_binding = root.bind("<Configure>", self._root_moved, add="+")
        self._arrow.configure(image=self._up_image)
        self._paint()
        popup.deiconify()
        popup.lift()
        popup.focus_force()
        popup.grab_set()

    def _root_moved(self, event):
        if event.widget == self.winfo_toplevel(): self.close(restore_focus=False)

    def _check_focus(self):
        self._focus_check = None
        if self._popup is None: return
        try:
            focus = self.focus_get()
            if focus is None or focus.winfo_toplevel() != self._popup:
                self.close(restore_focus=False)
        except tk.TclError: self.close(restore_focus=False)

    def _defer_focus_check(self, event):
        if self._popup is not None and self._focus_check is None:
            self._focus_check = self.after_idle(self._check_focus)

    def _close_after_dpi(self):
        self._dpi_close = None
        self.close(restore_focus=False)

    def _outside_click(self, event):
        popup = self._popup
        if popup and not (popup.winfo_rootx() <= event.x_root < popup.winfo_rootx()+popup.winfo_width()
                and popup.winfo_rooty() <= event.y_root < popup.winfo_rooty()+popup.winfo_height()):
            self.close()

    def _highlight(self, index):
        self._active_index = index
        for i, row in enumerate(self._rows):
            selected = self._values[i] == self._value
            row.configure(fg_color=Colors.STATUS_ACTIVE_FG if selected else Colors.CARD_HOVER if i == index else "transparent")
        return "break"

    def _move(self, direction):
        return self._highlight((self._active_index+direction) % len(self._values))

    def _select(self, index):
        value = self._values[index]
        self.set(value)
        self.close()
        if self._command: self._command(value)
        return "break"

    def _release_row(self, event, index):
        row = self._rows[index]
        if row.winfo_rootx() <= event.x_root < row.winfo_rootx()+row.winfo_width() and \
                row.winfo_rooty() <= event.y_root < row.winfo_rooty()+row.winfo_height():
            self._select(index)
        return "break"

    def _dismiss_key(self):
        self.close()
        return "break"

    def _tab(self, backwards):
        target = self._canvas.tk_focusPrev() if backwards else self._canvas.tk_focusNext()
        self.close(restore_focus=False)
        if target: target.focus_set()
        return "break"

    def close(self, restore_focus=True):
        popup, self._popup = self._popup, None
        if popup is None: return
        if self._focus_check is not None:
            self.after_cancel(self._focus_check)
            self._focus_check = None
        if self._dpi_close is not None:
            self.after_cancel(self._dpi_close)
            self._dpi_close = None
        if self._root_binding:
            self.winfo_toplevel().unbind("<Configure>", self._root_binding)
            self._root_binding = None
        try:
            if popup.grab_current() == popup: popup.grab_release()
            popup.destroy()
        except tk.TclError: pass
        ctk.ScalingTracker.remove_window(None, popup)
        ctk.ScalingTracker.window_dpi_scaling_dict.pop(popup, None)
        self._rows = []
        self._arrow.configure(image=self._down_image)
        self._leave(None)
        if restore_focus: self.focus_set()
        self._paint()

    def destroy(self):
        self.close(restore_focus=False)
        super().destroy()
