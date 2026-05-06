import subprocess
import threading
import time
import os
from gui.config import SCRCPY_PATH
from gui.i18n import tr


class ScreenCastManager:

    def __init__(self):
        self.adb_client = None
        self._scrcpy_process = None
        self.stream_active = False
        self._monitor_thread = None
        self._monitor_running = False
        self._on_state_change_callback = None

    def set_adb_client(self, adb_client):
        self.adb_client = adb_client

    def set_on_state_change_callback(self, callback):
        self._on_state_change_callback = callback

    def _get_phone_resolution(self):
        try:
            out, ok = self.adb_client.run_adb("shell", "wm", "size")
            if ok and out:
                size_str = out.split(":")[-1].strip()
                w, h = size_str.split("x")
                return int(w), int(h)
        except Exception:
            pass
        return 0, 0

    def _process_monitor(self):
        while self._monitor_running:
            if self._scrcpy_process:
                if self._scrcpy_process.poll() is not None:
                    self._on_scrcpy_exited()
                    break
            time.sleep(0.1)

    def _on_scrcpy_exited(self):
        if self.stream_active and self.adb_client:
            self.adb_client.log(tr("screen_cast_stopping"))
        self._scrcpy_process = None
        self.stream_active = False
        if self._on_state_change_callback:
            self._on_state_change_callback(False)

    def start_stream(self):
        if not self.adb_client or not self.adb_client.current_device:
            self.adb_client.log(tr("screen_cast_not_connected"), True)
            return
        
        if self._scrcpy_process and self._scrcpy_process.poll() is None:
            self.adb_client.log(tr("screen_cast_already_running"))
            return
        
        self.adb_client.log(tr("screen_cast_starting"))
        self._stop_scrcpy()

        try:
            import tkinter as tk
            temp_root = tk.Tk()
            temp_root.withdraw()
            screen_w = temp_root.winfo_screenwidth()
            screen_h = temp_root.winfo_screenheight() - 80
            temp_root.destroy()
        except Exception:
            screen_w, screen_h = 1920, 1000
        
        phone_w, phone_h = self._get_phone_resolution()
        if phone_w and phone_h:
            aspect = phone_w / phone_h
            calc_w = int(screen_h * aspect)
            if calc_w > screen_w:
                calc_w = screen_w
                screen_h = int(calc_w / aspect)
            window_w, window_h = calc_w, screen_h
        else:
            window_w, window_h = 600, 1000

        cmd = [
            str(SCRCPY_PATH),
            "-s", self.adb_client.current_device,
            "--window-width", str(window_w),
            "--window-height", str(window_h),
            "--video-bit-rate", "8M",
            "--max-fps", "25",
            "--always-on-top",
        ]

        try:
            env = os.environ.copy()
            env["PATH"] = str(SCRCPY_PATH.parent) + os.pathsep + env.get("PATH", "")
            self._scrcpy_process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
                creationflags=subprocess.CREATE_NO_WINDOW)
            self.stream_active = True
            if self._on_state_change_callback:
                self._on_state_change_callback(True)
            self.adb_client.log(tr("screen_cast_scrcpy_started", pid=self._scrcpy_process.pid))

            self._monitor_running = True
            self._monitor_thread = threading.Thread(target=self._process_monitor, daemon=True)
            self._monitor_thread.start()

            def read_stderr():
                try:
                    if stderr_output := self._scrcpy_process.stderr.read():
                        for line in stderr_output.decode("utf-8", errors="replace").strip().split("\n"):
                            if line.strip():
                                self.adb_client.log(f"[scrcpy] {line.strip()}", True)
                except Exception:
                    pass

            threading.Thread(target=read_stderr, daemon=True).start()

        except Exception as e:
            self.adb_client.log(tr("screen_cast_scrcpy_failed", error=e), True)
            self.stream_active = False
            if self._on_state_change_callback:
                self._on_state_change_callback(False)

    def _stop_scrcpy(self):
        self._monitor_running = False
        if self._scrcpy_process:
            try:
                self._scrcpy_process.terminate()
                self._scrcpy_process.wait(timeout=2)
            except Exception:
                try:
                    self._scrcpy_process.kill()
                except Exception:
                    pass
            self._scrcpy_process = None

    def toggle_stream(self):
        if self.stream_active:
            if self.adb_client:
                self.adb_client.log(tr("screen_cast_stopping"))
            self._stop_scrcpy()
            self.stream_active = False
            if self._on_state_change_callback:
                self._on_state_change_callback(False)
        else:
            self.start_stream()

    def take_screenshot(self):
        if not self.adb_client or not self.adb_client.current_device:
            return
        from tkinter import filedialog
        if save_path := filedialog.asksaveasfilename(
                title=tr("screen_cast_save_screenshot_title"), defaultextension=".png", filetypes=[(tr("screen_cast_png_images"), "*.png")]):
            phone_file = "/sdcard/screenshot_save.png"
            self.adb_client.run_adb("shell", "screencap", "-p", phone_file)
            self.adb_client.run_adb("pull", phone_file, save_path)
            self.adb_client.run_adb("shell", "rm", phone_file)
            self.adb_client.log(tr("screen_cast_save_success", path=save_path))
