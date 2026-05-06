import tkinter as tk
from tkinter import ttk
from gui.i18n import tr


class KeySimulationWidget:

    def __init__(self, parent, adb_client):
        self.adb_client = adb_client

        self.frame = ttk.LabelFrame(parent, text="")
        self._build_widgets()

    def _build_widgets(self):
        key_row = ttk.Frame(self.frame)
        key_row.pack(fill="x", padx=5, pady=3)

        for text_key, code in [
            ("home_key_back", 4),
            ("home_key_home", 3),
            ("home_key_recents", 187),
        ]:
            btn = ttk.Button(key_row, text="", command=lambda c=code: self._press_key(c))
            btn.pack(side="left", padx=3)
            setattr(self, f"btn_{text_key}", btn)

        ttk.Separator(key_row, orient="vertical").pack(side="left", padx=8, fill="y")

        for text_key, code in [
            ("home_key_vol_up", 24),
            ("home_key_vol_down", 25),
            ("home_key_mute", 164),
        ]:
            btn = ttk.Button(key_row, text="", command=lambda c=code: self._press_key(c))
            btn.pack(side="left", padx=3)
            setattr(self, f"btn_{text_key}", btn)
        
        ttk.Separator(key_row, orient="vertical").pack(side="left", padx=8, fill="y")

        btn_power = ttk.Button(key_row, text="", command=lambda: self._press_key(26))
        btn_power.pack(side="left", padx=3)
        self.btn_home_key_power = btn_power
        
        btn_power_long = ttk.Button(key_row, text="", command=lambda: self._long_press_key(26))
        btn_power_long.pack(side="left", padx=3)
        self.btn_home_key_power_long = btn_power_long

        ttk.Separator(key_row, orient="vertical").pack(side="left", padx=8, fill="y")

        self.btn_stream_toggle = ttk.Button(key_row, text="")
        self.btn_stream_toggle.pack(side="left", padx=3)
        self.btn_screenshot = ttk.Button(key_row, text="")
        self.btn_screenshot.pack(side="left", padx=3)

    def _press_key(self, code):
        if self.adb_client and self.adb_client.current_device:
            self.adb_client.run_adb_cmd(f"shell input keyevent {code}")

    def _long_press_key(self, code):
        if self.adb_client and self.adb_client.current_device:
            self.adb_client.run_adb_cmd(f"shell input keyevent --longpress {code}")

    def refresh_ui(self):
        self.frame.config(text=tr("home_key_frame"))
        if hasattr(self, "btn_home_key_back"):
            self.btn_home_key_back.config(text=tr("home_key_back"))
        if hasattr(self, "btn_home_key_home"):
            self.btn_home_key_home.config(text=tr("home_key_home"))
        if hasattr(self, "btn_home_key_recents"):
            self.btn_home_key_recents.config(text=tr("home_key_recents"))
        if hasattr(self, "btn_home_key_vol_up"):
            self.btn_home_key_vol_up.config(text=tr("home_key_vol_up"))
        if hasattr(self, "btn_home_key_vol_down"):
            self.btn_home_key_vol_down.config(text=tr("home_key_vol_down"))
        if hasattr(self, "btn_home_key_mute"):
            self.btn_home_key_mute.config(text=tr("home_key_mute"))
        if hasattr(self, "btn_home_key_power"):
            self.btn_home_key_power.config(text=tr("home_key_power"))
        if hasattr(self, "btn_home_key_power_long"):
            self.btn_home_key_power_long.config(text=tr("home_key_power_long"))
        if hasattr(self, "btn_stream_toggle"):
            self.btn_stream_toggle.config(text=tr("home_stream_btn"))
        if hasattr(self, "btn_screenshot"):
            self.btn_screenshot.config(text=tr("home_screenshot_btn"))
