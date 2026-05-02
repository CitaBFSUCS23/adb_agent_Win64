import tkinter as tk
from tkinter import ttk
from gui.utils import BasePage
from gui.i18n import tr

_REBOOT_CMDS = [
    ("home_reboot", "shell reboot", 0, 0),
    ("home_fastboot", "reboot bootloader", 0, 1),
    ("home_edl", "reboot edl", 0, 2),
    ("home_shutdown", "shell reboot -p", 1, 0),
    ("home_recovery", "reboot recovery", 1, 2),
]
_INFO_KEYS = [
    "home_brand", "home_model", "home_codename", "home_system",
    "home_cpu", "home_storage", "home_display", "home_uptime",
    "home_battery", "home_board", "home_platform", "home_build", "home_kernel",
]


class HomePage(BasePage):

    def __init__(self, parent):
        super().__init__(parent)
        self.screen_cast = None

        self.device_frame = ttk.LabelFrame(self.frame, text="")
        self.device_frame.pack(fill="x", padx=5, pady=5)
        inner = ttk.Frame(self.device_frame)
        inner.pack(fill="x", padx=5, pady=5)
        self.lbl_device = ttk.Label(inner, text="")
        self.lbl_device.pack(side="left")
        self.device_combo = ttk.Combobox(inner, state="readonly", width=25)
        self.device_combo.pack(side="left", padx=5)
        self.btn_refresh = ttk.Button(inner, text="", command=self._refresh_devices)
        self.btn_refresh.pack(side="left", padx=4)
        self.btn_netdebug = ttk.Button(inner, text="", command=self._start_network_debug)
        self.btn_netdebug.pack(side="left", padx=4)

        self.info_frame = ttk.LabelFrame(self.frame, text="")
        self.info_frame.pack(fill="both", expand=True, padx=5, pady=5)
        info_inner = ttk.Frame(self.info_frame)
        info_inner.pack(fill="both", expand=True, padx=5, pady=5)
        self.info_labels = {}
        self.info_label_widgets = {}
        for name in _INFO_KEYS:
            row = ttk.Frame(info_inner)
            row.pack(fill="x", pady=2)
            lbl_key = ttk.Label(row, text="", width=12)
            lbl_key.pack(side="left")
            lbl = ttk.Label(row, text="")
            lbl.pack(side="left", fill="x", expand=True)
            self.info_labels[name] = lbl
            self.info_label_widgets[name] = lbl_key

        self.reboot_frame = ttk.LabelFrame(self.frame, text="")
        self.reboot_frame.pack(fill="x", padx=5, pady=5)
        self.reboot_buttons = []
        reboot_row = ttk.Frame(self.reboot_frame)
        reboot_row.pack(fill="x", padx=5, pady=5)
        for text_key, cmd, r, c in _REBOOT_CMDS:
            btn = ttk.Button(reboot_row, text="", command=lambda c_cmd=cmd: self._run(c_cmd))
            btn.pack(side="left", padx=3)
            self.reboot_buttons.append((btn, text_key))

        self._network_dialog_widgets = {}
        self.refresh_ui()

    def set_adb_client(self, adb_client):
        super().set_adb_client(adb_client)

    def set_screen_cast(self, screen_cast):
        self.screen_cast = screen_cast

    def refresh_ui(self):
        self.device_frame.config(text=tr("home_device_list"))
        self.lbl_device.config(text=tr("home_device_label") + ":")
        self.btn_refresh.config(text=tr("home_refresh_btn"))
        self.btn_netdebug.config(text=tr("home_network_debug_btn"))
        self.info_frame.config(text=tr("home_info_frame"))
        self.reboot_frame.config(text=tr("home_reboot_frame"))
        for btn, text_key in self.reboot_buttons:
            btn.config(text=tr(text_key))
        for lbl_key in _INFO_KEYS:
            if lbl_key in self.info_label_widgets:
                self.info_label_widgets[lbl_key].config(text=tr(lbl_key) + ":")

    def _refresh_devices(self):
        if not self.adb_client:
            return
        if devices := self.adb_client.refresh_devices():
            self.device_combo["values"] = devices
            self.device_combo.set(devices[0])
            self.adb_client.current_device = devices[0]
            self.load_device_info()

    def _start_network_debug(self):
        if not self.adb_client:
            return
        dialog = tk.Toplevel(self.frame)
        dialog.title(tr("network_debug_title"))
        dialog.geometry("350x150")
        dialog.resizable(False, False)
        dialog.transient(self.frame)
        dialog.grab_set()

        entries = {}
        for i, label_key in enumerate(["network_debug_ip", "network_debug_port"]):
            ttk.Label(dialog, text=tr(label_key)).grid(row=i, column=0, padx=5, pady=5, sticky="e")
            entry = ttk.Entry(dialog, width=20)
            entry.grid(row=i, column=1, padx=5, pady=5)
            entries[i] = entry

        def do_connect():
            ip, port = entries[0].get().strip(), entries[1].get().strip()
            if not ip or not port:
                self._log(tr("network_debug_ip_port_empty"), True)
                return
            dialog.destroy()
            self._log(tr("network_debug_connecting", ip=ip, port=port))
            output, ok = self.adb_client.run_adb_cmd(f"connect {ip}:{port}")
            if ok and "connected" in (output or "").lower():
                self._log(tr("network_debug_connected", ip=ip, port=port))
                self._refresh_devices()
            else:
                self._log(tr("network_debug_failed", error=output or "No response"), True)

        btn_frame = ttk.Frame(dialog)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=15)
        ttk.Button(btn_frame, text=tr("network_debug_connect"), command=do_connect).pack(side="left", padx=5)
        ttk.Button(btn_frame, text=tr("network_debug_cancel"), command=dialog.destroy).pack(side="left", padx=5)
        entries[0].focus()
        entries[0].icursor("end")
        dialog.bind("<Return>", lambda e: do_connect())

    def _get_prop(self, prop):
        out, _ = self.adb_client.run_adb_cmd(f"shell getprop {prop}")
        return out or ""

    @staticmethod
    def _extract(text, key):
        return next((l.split(":")[1].strip() for l in text.split("\n") if f"{key}:" in l), "")

    @staticmethod
    def _last_line_value(text):
        if not text or ":" not in text:
            return ""
        return text.split("\n")[-1].split(":")[-1].strip().split()[0]

    def load_device_info(self):
        if not self.adb_client or not self.adb_client.current_device:
            return
        g = self._get_prop
        brand, model, codename = g("ro.product.brand"), g("ro.product.model"), g("ro.product.device")
        android, api = g("ro.build.version.release"), g("ro.build.version.sdk")
        cpu, storage = g("ro.product.cpu.abi"), g("ro.hardware.egl") or g("ro.boot.hardware.platform")

        disp, _ = self.adb_client.run_adb_cmd("shell wm size")
        dpi, _ = self.adb_client.run_adb_cmd("shell wm density")
        size, density = self._last_line_value(disp), self._last_line_value(dpi)
        display_info = f"{size}({density}dpi)" if size and density else ""

        batt, _ = self.adb_client.run_adb_cmd("shell dumpsys battery")
        batt_info = ""
        if batt and (level := self._extract(batt, "level")):
            batt_info = f"{level}% {self._extract(batt, 'voltage')}mV {self._extract(batt, 'temperature')}°C"

        uptime, _ = self.adb_client.run_adb_cmd("shell uptime")
        kernel = g("ro.version") or (self.adb_client.run_adb_cmd("shell uname -r")[0] or "")

        data = {
            "home_brand": brand,
            "home_model": model,
            "home_codename": codename,
            "home_system": f"Android {android} (API{api})",
            "home_cpu": cpu,
            "home_storage": storage,
            "home_display": display_info,
            "home_uptime": uptime or "",
            "home_battery": batt_info,
            "home_board": g("ro.product.board"),
            "home_platform": g("ro.board.platform"),
            "home_build": g("ro.build.fingerprint"),
            "home_kernel": kernel,
        }
        for k, v in data.items():
            if k in self.info_labels:
                self.info_labels[k].config(text=v)
