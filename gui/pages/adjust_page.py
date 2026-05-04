import tkinter as tk
from tkinter import ttk
from gui.utils import BasePage
from gui.i18n import tr

_SCALE_DEFS = [
    ("adjust_font_size", "font", 0.5, 2.0, 1.0, "{:.1f}"),
    ("adjust_anim_speed", "anim", 0.0, 10.0, 1.0, "{:.1f}"),
    ("adjust_screen_off", "screen_off", 5000, 300000, 30000, "{}ms"),
    ("adjust_brightness", "brightness", 0, 255, 100, "{}"),
]

_LOAD_CMDS = {
    "font": ("shell settings get system font_scale", float),
    "anim": ("shell settings get global window_animation_scale", float),
    "screen_off": ("shell settings get system screen_off_timeout", int),
    "brightness": ("shell settings get system screen_brightness", int),
}

_SET_CMDS = {
    "font": lambda v: f"shell settings put system font_scale {v}",
    "anim": lambda v: [f"shell settings put global {p} {v}" for p in
                       ("window_animation_scale", "transition_animation_scale", "animator_duration_scale")],
    "screen_off": lambda v: f"shell settings put system screen_off_timeout {int(v)}",
    "brightness": lambda v: f"shell settings put system screen_brightness {int(v)}",
}


class AdjustPage(BasePage):

    def __init__(self, parent):
        super().__init__(parent)
        self.scales = {}
        self.scale_frames = {}
        for title_key, key, from_, to, default, fmt in _SCALE_DEFS:
            self._create_scale(title_key, key, from_, to, default, fmt)
        self.refresh_ui()

    def _create_scale(self, title_key, key, from_, to, default, fmt):
        frame = ttk.LabelFrame(self.frame, text="")
        frame.pack(fill="x", padx=5, pady=5)
        inner = ttk.Frame(frame)
        inner.pack(fill="x", padx=5, pady=5)

        var = tk.DoubleVar(value=default) if isinstance(default, float) else tk.IntVar(value=default)
        scale = ttk.Scale(inner, from_=from_, to=to, orient="horizontal", variable=var)
        scale.pack(side="left", fill="x", expand=True)
        scale.bind("<ButtonRelease-1>", lambda e: self._on_set(key))
        scale.bind("<B1-Motion>", lambda e: self._update_label(key))

        label = ttk.Label(inner, text=fmt.format(default), width=10)
        label.pack(side="left", padx=5)
        self.scales[key] = {"var": var, "label": label, "fmt": fmt, "title_key": title_key}
        self.scale_frames[key] = frame
        
        if key == "brightness":
            btn_frame = ttk.Frame(frame)
            btn_frame.pack(fill="x", padx=5, pady=5)
            self.btn_brightness_auto_on = ttk.Button(btn_frame, text="", command=self._on_brightness_auto_on)
            self.btn_brightness_auto_on.pack(side="left", padx=2)
            self.btn_brightness_auto_off = ttk.Button(btn_frame, text="", command=self._on_brightness_auto_off)
            self.btn_brightness_auto_off.pack(side="left", padx=2)
    
    def _on_brightness_auto_on(self):
        if self.adb_client and self.adb_client.current_device:
            self.adb_client.run_adb_cmd("shell settings put system screen_brightness_mode 1")
    
    def _on_brightness_auto_off(self):
        if self.adb_client and self.adb_client.current_device:
            self.adb_client.run_adb_cmd("shell settings put system screen_brightness_mode 0")
    
    def refresh_ui(self):
        for key, info in self.scales.items():
            self.scale_frames[key].config(text=tr(info["title_key"]))
        if "brightness" in self.scales:
            if hasattr(self, "btn_brightness_auto_on"):
                self.btn_brightness_auto_on.config(text=tr("adjust_brightness_auto_on"))
            if hasattr(self, "btn_brightness_auto_off"):
                self.btn_brightness_auto_off.config(text=tr("adjust_brightness_auto_off"))

    def load_adjust_info(self):
        if not self.adb_client or not self.adb_client.current_device:
            return
        for key, (cmd, cast) in _LOAD_CMDS.items():
            out, _ = self.adb_client.run_adb_cmd(cmd)
            try:
                val = cast(out)
            except (ValueError, TypeError):
                continue
            self.scales[key]["var"].set(val)
            self.scales[key]["label"].config(text=self.scales[key]["fmt"].format(val))

    def _update_label(self, key):
        s = self.scales[key]
        s["label"].config(text=s["fmt"].format(s["var"].get()))

    def _on_set(self, key):
        s = self.scales[key]
        val = s["var"].get()
        if isinstance(val, float):
            val = round(val, 1)
            s["var"].set(val)
        s["label"].config(text=s["fmt"].format(val))
        cmds = _SET_CMDS[key](val)
        if isinstance(cmds, str):
            self._run(cmds)
        else:
            for cmd in cmds:
                self._run(cmd)
