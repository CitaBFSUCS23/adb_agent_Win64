import subprocess
from tkinter import ttk
from gui.config import ADB_PATH
from gui.i18n import tr

_NO_DEVICE_CMDS = frozenset(("connect", "disconnect", "devices", "kill-server", "start-server", "version"))


class ADBClient:

    def __init__(self, log_callback=None):
        self.current_device = None
        self.log_callback = log_callback

    def log(self, message, is_error=False):
        if self.log_callback:
            self.log_callback(message, is_error)

    def run_adb(self, *args, device=None):
        cmd = [ADB_PATH]
        if target := device or self.current_device:
            cmd.extend(["-s", target])
        cmd.extend(args)
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
            return r.stdout.strip(), r.returncode == 0
        except Exception as e:
            return str(e), False

    def run_adb_cmd(self, *args):
        cmd_parts = args[0].split() if len(args) == 1 and isinstance(args[0], str) else args
        cmd_str = " ".join(cmd_parts)
        if not self.current_device and not any(cmd_str.startswith(c) for c in _NO_DEVICE_CMDS):
            self.log(tr("common_select_device"), True)
            return None, False
        self.log(f"$ {cmd_str}")
        output, ok = self.run_adb(*cmd_parts)
        if output:
            self.log(output, not ok)
        return output, ok

    def refresh_devices(self):
        self.log(tr("common_refreshing"))
        output, ok = self.run_adb("devices")
        return [l.split()[0] for l in output.split("\n") if "\t" in l] if ok else []


class BasePage:

    def __init__(self, parent):
        self.frame = ttk.Frame(parent)
        self.adb_client = None

    def set_adb_client(self, adb_client):
        self.adb_client = adb_client

    def _run(self, cmd):
        if self.adb_client:
            self.adb_client.run_adb_cmd(cmd)

    def _log(self, message, is_error=False):
        if self.adb_client:
            self.adb_client.log(message, is_error)

    @staticmethod
    def _set_entry(entry, value):
        entry.delete(0, "end")
        entry.insert(0, str(value))

    @staticmethod
    def tr(key, **kwargs):
        return tr(key, **kwargs)
