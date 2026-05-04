import tkinter as tk
from tkinter import ttk
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gui.utils import ADBClient
from gui.widgets.adb_terminal import ADBTerminal
from gui.widgets.screen_cast import ScreenCastManager
from gui.pages.home_page import HomePage
from gui.pages.software_page import SoftwarePage
from gui.pages.display_page import DisplayPage
from gui.pages.battery_page import BatteryPage
from gui.pages.adjust_page import AdjustPage
from gui.pages.script_page import ScriptPage
from gui.pages.agent_page import AgentPage
from gui.config import NAV_PAGES, DEFAULT_LANG
from gui.i18n import tr, set_lang, get_lang, available_langs

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
        main_vertical_paned.add(top_horizontal_paned, weight=1)

        left_frame = ttk.Frame(top_horizontal_paned)
        top_horizontal_paned.add(left_frame, weight=1)

        top_frame = ttk.Frame(left_frame)
        top_frame.pack(fill="x", padx=5, pady=5)
        self.lbl_lang = ttk.Label(top_frame, text="")
        self.lbl_lang.pack(side="left", padx=2)
        self.lang_combo = ttk.Combobox(top_frame, values=available_langs(), state="readonly", width=10)
        self.lang_combo.set(get_lang())
        self.lang_combo.pack(side="left", padx=2)
        self.lang_combo.bind("<<ComboboxSelected>>", self._on_lang_changed)

        nav_frame = ttk.Frame(left_frame)
        nav_frame.pack(fill="x", padx=5, pady=5)
        self.nav_buttons = []
        for i, (_, page_key) in enumerate(NAV_PAGES):
            btn = ttk.Button(nav_frame, text="", width=8,
                           command=lambda idx=i: self.show_page(idx))
            btn.pack(side="left", padx=1)
            self.nav_buttons.append(btn)

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
        top_horizontal_paned.add(center_frame, weight=1)
        self.adb_terminal = ADBTerminal(center_frame)
        self.adb_terminal.set_adb_client(self.adb_client)

        self.key_frame = ttk.LabelFrame(main_vertical_paned, text="")
        main_vertical_paned.add(self.key_frame, weight=0)
        self._build_key_bar(self.key_frame)

        self.screen_cast_manager = ScreenCastManager()
        self.screen_cast_manager.set_adb_client(self.adb_client)

        for pc in self.page_classes.values():
            pc.set_adb_client(self.adb_client)

        self._refresh_language()
        self._initial_refresh()

    def _build_key_bar(self, parent):
        self.key_buttons = []
        self.long_press_buttons = []
        key_row = ttk.Frame(parent)
        key_row.pack(fill="x", padx=5, pady=3)
        
        # Navigation group: Back, Home, Recents
        for text_key, code in [
            ("home_key_back", 4),
            ("home_key_home", 3),
            ("home_key_recents", 187),
        ]:
            btn = ttk.Button(key_row, text="", command=lambda c=code: self.adb_client.run_adb_cmd(f"shell input keyevent {c}"))
            btn.pack(side="left", padx=3)
            self.key_buttons.append((btn, text_key))
        
        # Separator 1
        ttk.Separator(key_row, orient="vertical").pack(side="left", padx=8, fill="y")
        
        # Volume group: Vol+, Vol-, Mute
        for text_key, code in [
            ("home_key_vol_up", 24),
            ("home_key_vol_down", 25),
            ("home_key_mute", 164),
        ]:
            btn = ttk.Button(key_row, text="", command=lambda c=code: self.adb_client.run_adb_cmd(f"shell input keyevent {c}"))
            btn.pack(side="left", padx=3)
            self.key_buttons.append((btn, text_key))
        
        # Separator 2
        ttk.Separator(key_row, orient="vertical").pack(side="left", padx=8, fill="y")
        
        # Power group: Power, Long Press Power
        for text_key, code in [
            ("home_key_power", 26),
        ]:
            btn = ttk.Button(key_row, text="", command=lambda c=code: self.adb_client.run_adb_cmd(f"shell input keyevent {c}"))
            btn.pack(side="left", padx=3)
            self.key_buttons.append((btn, text_key))
            lp_btn = ttk.Button(key_row, text="", command=lambda c=code: self.adb_client.run_adb_cmd(f"shell input keyevent --longpress {c}"))
            lp_btn.pack(side="left", padx=3)
            self.long_press_buttons.append((lp_btn, "home_key_power_long"))
        
        # Separator 3
        ttk.Separator(key_row, orient="vertical").pack(side="left", padx=8, fill="y")

        self.btn_stream_toggle = ttk.Button(key_row, text="", command=self._toggle_stream)
        self.btn_stream_toggle.pack(side="left", padx=3)
        self.btn_screenshot = ttk.Button(key_row, text="", command=self._take_screenshot)
        self.btn_screenshot.pack(side="left", padx=3)

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
        self.lbl_lang.config(text=tr("main_language_label"))
        for i, btn in enumerate(self.nav_buttons):
            btn.config(text=tr(NAV_PAGES[i][1]))
        self.adb_terminal.refresh_ui()
        for pc in self.page_classes.values():
            if hasattr(pc, "refresh_ui"):
                pc.refresh_ui()
        for btn, text_key in self.key_buttons:
            btn.config(text=tr(text_key))
        for btn, text_key in self.long_press_buttons:
            btn.config(text=tr(text_key))
        self.key_frame.config(text=tr("home_key_frame"))
        self.btn_stream_toggle.config(text=tr("home_stream_btn"))
        self.btn_screenshot.config(text=tr("home_screenshot_btn"))

    def _on_lang_changed(self, event=None):
        if new_lang := self.lang_combo.get():
            set_lang(new_lang)
            self._refresh_language()

    def _initial_refresh(self):
        devices = self.adb_client.refresh_devices()
        home = self.page_classes["home"]
        home.device_combo["values"] = devices
        if devices:
            home.device_combo.set(devices[0])
            self.adb_client.current_device = devices[0]
            home.load_device_info()
        home.device_combo.bind("<<ComboboxSelected>>", self._on_device_changed)

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
