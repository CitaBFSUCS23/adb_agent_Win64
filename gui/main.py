import tkinter as tk
from tkinter import ttk
import sys
import os
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gui.utils import ADBClient
from gui.widgets.adb_terminal import ADBTerminal
from gui.widgets.screen_cast import ScreenCastManager
from gui.widgets.key_simulation import KeySimulationWidget
from gui.widgets.language_and_nav import languageAndNavWidget
from gui.pages.home_page import HomePage
from gui.pages.software_page import SoftwarePage
from gui.pages.display_page import DisplayPage
from gui.pages.battery_page import BatteryPage
from gui.pages.adjust_page import AdjustPage
from gui.pages.script_page import ScriptPage
from gui.pages.agent_page import AgentPage
from gui.config import NAV_PAGES, DEFAULT_LANG
from gui.i18n import tr, set_lang

_PAGE_CLASSES = [HomePage, SoftwarePage, DisplayPage, BatteryPage, AdjustPage, ScriptPage, AgentPage]

_AUTO_REFRESH = {"display", "battery", "adjust"}


class MainApp:

    def __init__(self, root):
        self.root = root
        self.root.state("zoomed")
        set_lang(DEFAULT_LANG)
        self.adb_client = ADBClient()

        main_vertical_paned = ttk.PanedWindow(self.root, orient=tk.VERTICAL)
        main_vertical_paned.pack(fill="both", expand=True)

        top_horizontal_paned = ttk.PanedWindow(main_vertical_paned, orient=tk.HORIZONTAL)
        main_vertical_paned.add(top_horizontal_paned)

        left_frame = ttk.Frame(top_horizontal_paned)
        top_horizontal_paned.add(left_frame)

        self.language_and_nav = languageAndNavWidget(left_frame, 
            on_lang_changed=self._on_lang_changed,
            on_nav_clicked=self.show_page)
        self.language_and_nav.frame.pack(fill="x")

        style = ttk.Style()
        style.layout('Hidden.TNotebook.Tab', [])
        self.console_notebook = ttk.Notebook(left_frame, style='Hidden.TNotebook')
        self.console_notebook.pack(fill="both", expand=True, padx=5, pady=5)

        self.page_classes = {}
        for (page_id, _), PageClass in zip(NAV_PAGES, _PAGE_CLASSES):
            page_obj = PageClass(left_frame)
            self.console_notebook.add(page_obj.frame, text="")
            self.page_classes[page_id] = page_obj

        center_frame = ttk.Frame(top_horizontal_paned)
        top_horizontal_paned.add(center_frame)
        self.adb_terminal = ADBTerminal(center_frame)
        self.adb_terminal.set_adb_client(self.adb_client)

        self.key_simulation = KeySimulationWidget(main_vertical_paned, self.adb_client)
        main_vertical_paned.add(self.key_simulation.frame)
        
        self.key_simulation.btn_stream_toggle.config(command=self._toggle_stream)
        self.key_simulation.btn_screenshot.config(command=self._take_screenshot)

        self.screen_cast_manager = ScreenCastManager()
        self.screen_cast_manager.set_adb_client(self.adb_client)

        for pc in self.page_classes.values():
            pc.set_adb_client(self.adb_client)
            if hasattr(pc, 'set_screen_cast_manager'):
                pc.set_screen_cast_manager(self.screen_cast_manager)

        self._refresh_language()
        self._initial_refresh()

    def _toggle_stream(self):
        if self.screen_cast_manager:
            if not self.screen_cast_manager.stream_active:
                self.screen_cast_manager.start_stream()

    def _take_screenshot(self):
        if self.screen_cast_manager:
            self.screen_cast_manager.take_screenshot()

    def show_page(self, index):
        self.console_notebook.select(index)
        if (page_id := NAV_PAGES[index][0]) in _AUTO_REFRESH:
            getattr(self.page_classes[page_id], f"load_{page_id}_info")()

    def _refresh_language(self):
        self.root.title(tr("main_title"))
        self.language_and_nav.refresh_ui()
        self.adb_terminal.refresh_ui()
        if hasattr(self, "key_simulation"):
            self.key_simulation.refresh_ui()
        for pc in self.page_classes.values():
            if hasattr(pc, "refresh_ui"):
                pc.refresh_ui()

    def _on_lang_changed(self):
        self._refresh_language()

    def _initial_refresh(self):
        threading.Thread(target=self._initial_refresh_async, daemon=True).start()

    def _initial_refresh_async(self):
        devices = self.adb_client.refresh_devices()
        if devices:
            self.root.after(0, lambda: self._update_initial_ui(devices))

    def _update_initial_ui(self, devices):
        home = self.page_classes["home"]
        home.device_combo["values"] = devices
        home.device_combo.set(devices[0])
        self.adb_client.current_device = devices[0]
        home.device_combo.bind("<<ComboboxSelected>>", self._on_device_changed)
        home.load_device_info()

    def _on_device_changed(self):
        if selected := self.page_classes["home"].device_combo.get():
            self.adb_client.current_device = selected
            self.page_classes["home"].load_device_info()


def main():
    root = tk.Tk()
    MainApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
