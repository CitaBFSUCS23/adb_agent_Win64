from tkinter import ttk
from gui.utils import BasePage
from gui.i18n import tr

_BATTERY_FIELDS = [("battery_level", "level"), ("battery_status", "status"), ("battery_temp", "temp"),
                   ("battery_voltage", "voltage"), ("battery_health", "health"), ("battery_tech", "tech")]
_BATTERY_MAPPING = {"level:": "level", "status:": "status", "temperature:": "temp",
                    "voltage:": "voltage", "health:": "health", "technology:": "tech"}
_CHARGE_BUTTONS = [
    ("battery_ac_on", "shell dumpsys battery set ac 1"), ("battery_ac_off", "shell dumpsys battery set ac 0"),
    ("battery_usb_on", "shell dumpsys battery set usb 1"), ("battery_usb_off", "shell dumpsys battery set usb 0"),
    ("battery_reset", "shell dumpsys battery reset"),
]


class BatteryPage(BasePage):

    def __init__(self, parent):
        super().__init__(parent)

        self.info_frame = ttk.LabelFrame(self.frame, text="")
        self.info_frame.pack(fill="x", padx=5, pady=5)
        self.battery_labels = {}
        self.battery_name_labels = {}
        for name_key, key in _BATTERY_FIELDS:
            lbl, name_lbl = self._info_row(self.info_frame, name_key, key)
            self.battery_labels[key] = lbl
            self.battery_name_labels[key] = name_lbl

        self.sim_frame = ttk.LabelFrame(self.frame, text="")
        self.sim_frame.pack(fill="x", padx=5, pady=5)

        level_row = ttk.Frame(self.sim_frame)
        level_row.pack(fill="x", padx=5, pady=5)
        self.lbl_level = ttk.Label(level_row, text="")
        self.lbl_level.pack(side="left")
        self.battery_level_entry = ttk.Entry(level_row, width=10)
        self.battery_level_entry.pack(side="left", padx=5)
        self.btn_set_level = ttk.Button(level_row, text="", command=self._set_battery_level)
        self.btn_set_level.pack(side="left", padx=3)

        self.charge_frame = ttk.Frame(self.sim_frame)
        self.charge_frame.pack(fill="x", padx=5, pady=5)
        self.charge_buttons = []
        for text_key, cmd in _CHARGE_BUTTONS:
            btn = ttk.Button(self.charge_frame, text="", command=lambda c=cmd: self._run(c))
            btn.pack(side="left", padx=3)
            self.charge_buttons.append((btn, text_key))
        
        self.refresh_ui()

    @staticmethod
    def _info_row(parent, name_key, key):
        row = ttk.Frame(parent)
        row.pack(fill="x", padx=5, pady=2)
        name_lbl = ttk.Label(row, text="", width=10)
        name_lbl.pack(side="left")
        lbl = ttk.Label(row, text="")
        lbl.pack(side="left", fill="x", expand=True)
        return lbl, name_lbl
    
    def refresh_ui(self):
        self.info_frame.config(text=tr("battery_info"))
        for name_key, key in _BATTERY_FIELDS:
            self.battery_name_labels[key].config(text=tr(name_key) + ":")
        self.sim_frame.config(text=tr("battery_sim"))
        self.lbl_level.config(text=tr("battery_level_percent"))
        self.btn_set_level.config(text=tr("battery_set_level"))
        for btn, text_key in self.charge_buttons:
            btn.config(text=tr(text_key))

    def load_battery_info(self):
        if not self.adb_client or not self.adb_client.current_device:
            return
        output, ok = self.adb_client.run_adb_cmd("shell dumpsys battery")
        if not (ok and output):
            return
        for line in output.split("\n"):
            s = line.strip()
            if key := next((k for k in _BATTERY_MAPPING if k in s), None):
                self.battery_labels[_BATTERY_MAPPING[key]].config(text=s.split(":")[1].strip())

    def _set_battery_level(self):
        if level := self.battery_level_entry.get().strip():
            self._run(f"shell dumpsys battery set level {level}")
