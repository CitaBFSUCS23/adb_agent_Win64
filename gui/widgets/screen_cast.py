# SPDX-License-Identifier: Apache-2.0
#
# This file uses scrcpy for screen casting functionality.
# scrcpy is licensed under the Apache License 2.0.
# Copyright (C) 2018 Genymobile
# Copyright (C) 2018-2021 Romain Vimont
# See: https://github.com/Genymobile/scrcpy

import tkinter as tk
from tkinter import ttk, filedialog
import os
import subprocess
import threading
from gui.config import SCRCPY_PATH
from gui.i18n import tr

_TOPMOST_FLAG = 0x00000008
_NOTOPMOST_FLAG = 0xFFFFFFF8
_SWP_NOSIZE = 0x0001
_SWP_NOMOVE = 0x0002


class ScreenCastWindow:

    def __init__(self, parent):
        self.adb_client = None
        self._scrcpy_process = None
        self.stream_active = False

        self.window = tk.Toplevel(parent)
        self.window.title(tr("screen_cast_window_title"))
        self.window.geometry("400x700")
        self.window.withdraw()
        self._set_always_on_top(True)

        btn_frame = ttk.Frame(self.window)
        btn_frame.pack(fill="x", padx=5, pady=5)
        self.btn_screenshot = ttk.Button(btn_frame, text="", command=self.take_screenshot)
        self.btn_screenshot.pack(side="left", padx=2)
        self.btn_toggle_stream = ttk.Button(btn_frame, text="", command=self._toggle_stream)
        self.btn_toggle_stream.pack(side="left", padx=2)
        self.btn_close_window = ttk.Button(btn_frame, text="", command=self.hide)
        self.btn_close_window.pack(side="right", padx=2)

    def set_adb_client(self, adb_client):
        self.adb_client = adb_client

    def show(self):
        self.window.deiconify()
        self._set_always_on_top(True)
        self.window.lift()
        self.window.focus_set()

    def hide(self):
        if self.stream_active:
            self._stop_scrcpy()
            self.stream_active = False
            self.btn_toggle_stream.config(text=tr("screen_cast_toggle_start"))
        self.window.withdraw()

    def _set_always_on_top(self, on):
        self.window.attributes("-topmost", on)

    def _container_size(self):
        self.window.update()
        w, h = self.window.winfo_width(), self.window.winfo_height()
        if w < 100 or h < 100:
            w, h = 400, 700
        return max(w, 300), max(h, 500)

    def start_stream(self):
        if not self.adb_client or not self.adb_client.current_device:
            self.adb_client.log(tr("screen_cast_not_connected"), True)
            return
        if self._scrcpy_process and self._scrcpy_process.poll() is None:
            self.adb_client.log(tr("screen_cast_already_running"))
            return

        self.stream_active = True
        self.adb_client.log(tr("screen_cast_starting"))
        self._stop_scrcpy()

        w, h = self._container_size()
        self.adb_client.log(tr("screen_cast_cast_size", width=w, height=h))

        cmd = [
            str(SCRCPY_PATH),
            "-s", self.adb_client.current_device,
            "--max-size", str(max(w, h)),
            "--window-width", str(w),
            "--window-height", str(h),
            "--video-bit-rate", "16M",
            "--max-fps", "60",
            "--window-title", "scrcpy",
            "--always-on-top",
        ]

        try:
            env = os.environ.copy()
            env["PATH"] = str(SCRCPY_PATH.parent) + os.pathsep + env.get("PATH", "")
            self._scrcpy_process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
                creationflags=subprocess.CREATE_NO_WINDOW)
            self.adb_client.log(tr("screen_cast_scrcpy_started", pid=self._scrcpy_process.pid))

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

    def _stop_scrcpy(self):
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

    def _toggle_stream(self):
        if self.stream_active:
            self.stream_active = False
            self._stop_scrcpy()
            self.btn_toggle_stream.config(text=tr("screen_cast_toggle_start"))
            self.adb_client.log(tr("screen_cast_stopping"))
        else:
            self.btn_toggle_stream.config(text=tr("screen_cast_toggle_stop"))
            self.start_stream()

    def take_screenshot(self):
        if not self.adb_client or not self.adb_client.current_device:
            return
        if save_path := filedialog.asksaveasfilename(
                title=tr("screen_cast_save_screenshot_title"), defaultextension=".png", filetypes=[(tr("screen_cast_png_images"), "*.png")]):
            phone_file = "/sdcard/screenshot_save.png"
            self.adb_client.run_adb("shell", "screencap", "-p", phone_file)
            self.adb_client.run_adb("pull", phone_file, save_path)
            self.adb_client.run_adb("shell", "rm", phone_file)
            self.adb_client.log(tr("screen_cast_save_success", path=save_path))

    def refresh_ui(self):
        self.window.title(tr("screen_cast_window_title"))
        self.btn_screenshot.config(text=tr("screen_cast_screenshot"))
        self.btn_close_window.config(text=tr("screen_cast_close_window"))
        if self.stream_active:
            self.btn_toggle_stream.config(text=tr("screen_cast_toggle_stop"))
        else:
            self.btn_toggle_stream.config(text=tr("screen_cast_toggle_start"))
