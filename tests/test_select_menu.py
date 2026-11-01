import unittest
import tkinter as tk
from types import SimpleNamespace
from unittest.mock import Mock, patch
import customtkinter as ctk
from ui.components.select_menu import SelectMenu


class TestSelectMenu(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = ctk.CTk()

    @classmethod
    def tearDownClass(cls):
        # These tests create a separate Tk interpreter before the AppWindow
        # tests. Do not leave CTk's shared polling timers on that interpreter.
        for task in cls.root.tk.call('after','info'):
            cls.root.after_cancel(task)
        cls.root.destroy()
        ctk.ScalingTracker.update_loop_running = False
        ctk.AppearanceModeTracker.update_loop_running = False

    def setUp(self):
        self.root.geometry('420x280+100+200')
        self.callback = Mock()
        self.select = SelectMenu(self.root, ['Máxima','320 kbps','192 kbps'], command=self.callback)
        self.select.pack(padx=20,pady=20)
        self.root.update()

    def tearDown(self):
        self.select.destroy()
        self.root.update()

    def test_programmatic_value_change_never_calls_user_callback(self):
        self.select.set('192 kbps')
        self.assertEqual(self.select.get(),'192 kbps')
        self.callback.assert_not_called()

    def test_open_rounded_popup_and_choose_option_releases_grab(self):
        self.select.open()
        self.root.update()
        self.assertIs(self.root.grab_current(),self.select._popup)
        self.assertIsInstance(self.select._popup,tk.Toplevel)
        self.assertEqual(self.select._popup.winfo_children()[0].cget('corner_radius'),12)
        self.select._move(1)
        self.select._select(self.select._active_index)
        self.assertEqual(self.select.get(),'320 kbps')
        self.callback.assert_called_once_with('320 kbps')
        self.assertIsNone(self.root.grab_current())
        self.assertIsNone(self.select._popup)

    def test_escape_keeps_previous_selection(self):
        self.select.open()
        self.select._move(1)
        self.select._dismiss_key()
        self.assertEqual(self.select.get(),'Máxima')
        self.callback.assert_not_called()
        self.assertIsNone(self.root.grab_current())

    def test_values_change_closes_popup_and_replaces_incompatible_selection(self):
        self.select.open()
        self.select.configure(values=['1080p','720p'])
        self.assertEqual(self.select.get(),'1080p')
        self.assertEqual(self.select.cget('values'),['1080p','720p'])
        self.assertIsNone(self.select._popup)
        self.assertIsNone(self.root.grab_current())
        self.callback.assert_not_called()

    def test_disabled_selector_cannot_open(self):
        self.select.configure(state='disabled')
        self.select.open()
        self.assertIsNone(self.select._popup)

    def test_popup_opens_above_when_there_is_no_space_below(self):
        bottom = self.select.winfo_rooty()+self.select.winfo_height()+10
        with patch.object(self.select,'_work_area',return_value=(0,0,1000,bottom)):
            self.select.open()
            self.root.update()
            self.assertLess(self.select._popup.winfo_rooty(),self.select.winfo_rooty())

    def test_parent_move_and_widget_destroy_dismiss_popup(self):
        self.select.open()
        self.root.geometry('+130+210')
        self.root.update()
        self.assertIsNone(self.select._popup)
        self.select.open()
        self.select.destroy()
        self.assertIsNone(self.root.grab_current())

    def test_other_modal_grab_is_never_replaced(self):
        modal = tk.Toplevel(self.root)
        modal.grab_set()
        self.select.open()
        self.assertIsNone(self.select._popup)
        self.assertIs(self.root.grab_current(),modal)
        modal.grab_release()
        modal.destroy()

    def test_theme_change_and_repeated_open_close_do_not_leak_popups(self):
        try:
            for theme in ('Light','Dark'):
                ctk.set_appearance_mode(theme)
                for _ in range(4):
                    self.select.open()
                    self.root.update()
                    self.select.close()
                    self.root.update()
                    self.assertIsNone(self.root.grab_current())
            self.assertFalse(any(isinstance(w,tk.Toplevel) for w in self.select.winfo_children()))
        finally: ctk.set_appearance_mode('Dark')

    def test_mouse_open_stops_ctk_global_focus_binding_and_row_click_selects(self):
        self.assertEqual(self.select._open_key(None),'break')
        self.root.update()
        row = self.select._rows[2]
        self.select._release_row(SimpleNamespace(x_root=row.winfo_rootx()+10,y_root=row.winfo_rooty()+10),2)
        self.callback.assert_called_once_with('192 kbps')
        self.assertIsNone(self.root.grab_current())

    def test_outside_click_dismisses_and_removes_dpi_registry_entry(self):
        self.select.open()
        self.root.update()
        popup = self.select._popup
        self.select._outside_click(SimpleNamespace(x_root=-10000,y_root=-10000))
        self.assertIsNone(self.select._popup)
        self.assertNotIn(popup,ctk.ScalingTracker.window_widgets_dict)
        self.assertNotIn(popup,ctk.ScalingTracker.window_dpi_scaling_dict)
        self.callback.assert_not_called()

    def test_dpi_change_dismisses_after_tracker_iteration(self):
        self.select.open()
        popup = self.select._popup
        popup.block_update_dimensions_event()
        popup.unblock_update_dimensions_event()
        self.assertIs(self.select._popup,popup)
        self.root.update()
        self.assertIsNone(self.select._popup)
        self.assertIsNone(self.root.grab_current())
