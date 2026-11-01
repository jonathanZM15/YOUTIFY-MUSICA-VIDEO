"""One desktop window per Windows session, independent of executable/data paths.

The named event coalesces repeated starts, including clicks during startup. No
files, sockets, warning dialogs or elevated permissions are required.
"""
import ctypes
from ctypes import wintypes
import sys
import hashlib

INSTANCE_NAME = r"Local\Youtify.Desktop.E3C6F949.1"
WINDOW_PROPERTY = "Youtify.MainWindow.E3C6F949"
ERROR_ALREADY_EXISTS = 183
WAIT_OBJECT_0 = 0


class SingleInstance:
    def __init__(self, name=INSTANCE_NAME):
        self.name = name
        self.window_property = WINDOW_PROPERTY + "." + hashlib.sha256(name.encode()).hexdigest()[:12]
        self._mutex = None
        self._event = None
        self._hwnd = None
        self.is_primary = False
        if sys.platform != "win32":
            raise OSError("SingleInstance requires Windows")
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.user = ctypes.WinDLL("user32", use_last_error=True)
        prototypes = {
            "CreateMutexW": ([ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR], wintypes.HANDLE),
            "CreateEventW": ([ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR], wintypes.HANDLE),
            "SetEvent": ([wintypes.HANDLE], wintypes.BOOL),
            "WaitForSingleObject": ([wintypes.HANDLE, wintypes.DWORD], wintypes.DWORD),
            "CloseHandle": ([wintypes.HANDLE], wintypes.BOOL),
        }
        for name, (args, result) in prototypes.items():
            function = getattr(self.kernel, name)
            function.argtypes, function.restype = args, result
        self.user.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
        self.user.GetAncestor.restype = wintypes.HWND
        self.user.SetPropW.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.HANDLE]
        self.user.SetPropW.restype = wintypes.BOOL
        self.user.GetPropW.argtypes = [wintypes.HWND, wintypes.LPCWSTR]
        self.user.GetPropW.restype = wintypes.HANDLE
        self.user.RemovePropW.argtypes = [wintypes.HWND, wintypes.LPCWSTR]
        self.user.RemovePropW.restype = wintypes.HANDLE
        self.user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        self.user.GetWindowThreadProcessId.restype = wintypes.DWORD
        self.user.AllowSetForegroundWindow.argtypes = [wintypes.DWORD]
        self.user.AllowSetForegroundWindow.restype = wintypes.BOOL
        self.user.ShowWindowAsync.argtypes = [wintypes.HWND, ctypes.c_int]
        self.user.ShowWindowAsync.restype = wintypes.BOOL
        self.user.SetForegroundWindow.argtypes = [wintypes.HWND]
        self.user.SetForegroundWindow.restype = wintypes.BOOL
        self._enum_callback = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        self.user.EnumWindows.argtypes = [self._enum_callback, wintypes.LPARAM]
        self.user.EnumWindows.restype = wintypes.BOOL

    def acquire(self):
        if self._mutex:
            return self.is_primary
        # Create the event first so a duplicate can signal even before Tk exists.
        self._event = self.kernel.CreateEventW(None, False, False, self.name + ".activate")
        if not self._event:
            raise ctypes.WinError(ctypes.get_last_error())
        ctypes.set_last_error(0)
        self._mutex = self.kernel.CreateMutexW(None, False, self.name)
        error = ctypes.get_last_error()
        if not self._mutex:
            self.close()
            raise ctypes.WinError(error)
        self.is_primary = error != ERROR_ALREADY_EXISTS
        if not self.is_primary:
            self._activate_existing()
            self.kernel.SetEvent(self._event)
        return self.is_primary

    def _activate_existing(self):
        @self._enum_callback
        def visit(hwnd, _):
            if self.user.GetPropW(hwnd, self.window_property) == 1:
                pid = wintypes.DWORD()
                self.user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                self.user.AllowSetForegroundWindow(pid.value)
                self.user.ShowWindowAsync(hwnd, 9)  # SW_RESTORE
                self.user.SetForegroundWindow(hwnd)
                return False
            return True
        self.user.EnumWindows(visit, 0)

    def attach(self, app):
        app.update_idletasks()
        self._hwnd = self.user.GetAncestor(app.winfo_id(), 2)  # GA_ROOT
        if not self.user.SetPropW(self._hwnd, self.window_property, 1):
            raise ctypes.WinError(ctypes.get_last_error())

        def poll():
            if app._closing:
                return
            if self.activation_requested():
                # Do not take the modal grab away from a file dialog/confirmation.
                modal = app.grab_current()
                target = modal.winfo_toplevel() if modal else app
                if app.state() == "iconic":
                    app.deiconify()
                target.lift()
                target.focus_force()
            app.after(150, poll)
        app.after(150, poll)

    def activation_requested(self):
        if not self._event:
            return False
        result = self.kernel.WaitForSingleObject(self._event, 0)
        if result == 0xFFFFFFFF:
            raise ctypes.WinError(ctypes.get_last_error())
        return result == WAIT_OBJECT_0

    def close(self):
        if self._hwnd:
            self.user.RemovePropW(self._hwnd, self.window_property)
            self._hwnd = None
        for attribute in ("_mutex", "_event"):
            handle = getattr(self, attribute)
            if handle:
                self.kernel.CloseHandle(handle)
                setattr(self, attribute, None)
        self.is_primary = False

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *_):
        self.close()
