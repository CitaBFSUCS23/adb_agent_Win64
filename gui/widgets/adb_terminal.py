import tkinter as tk
from tkinter import ttk, scrolledtext
import time
from gui.i18n import tr


class ADBTerminal:

    def __init__(self, parent):
        self.frame = ttk.LabelFrame(parent, text="")
        self.frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.log_text = scrolledtext.ScrolledText(self.frame, state="disabled", font=("Consolas", 10), wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)
        self.log_text.tag_config("error", foreground="red")
        self.log_text.tag_config("normal", foreground="black")

        input_frame = ttk.Frame(self.frame)
        input_frame.pack(fill="x", padx=5, pady=5)
        self.quick_cmd_entry = ttk.Entry(input_frame, font=("Consolas", 10))
        self.quick_cmd_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.quick_cmd_entry.bind("<Return>", lambda e: self._exec_quick_cmd())
        self.btn_exec = ttk.Button(input_frame, text="", command=self._exec_quick_cmd)
        self.btn_exec.pack(side="right", padx=3)
        self.btn_clear = ttk.Button(input_frame, text="", command=self.clear_log)
        self.btn_clear.pack(side="right", padx=3)

        self.adb_client = None

    def set_adb_client(self, adb_client):
        self.adb_client = adb_client
        adb_client.log_callback = self.log

    def log(self, message, is_error=False):
        self.log_text.config(state="normal")
        self.log_text.insert("end", f"[{time.strftime('%H:%M:%S')}] {message}\n", "error" if is_error else "normal")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def clear_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")

    def _exec_quick_cmd(self):
        if (cmd := self.quick_cmd_entry.get().strip()) and self.adb_client:
            self.adb_client.run_adb_cmd(cmd)
            self.quick_cmd_entry.delete(0, "end")

    def refresh_ui(self):
        self.frame.config(text=tr("adb_terminal_frame"))
        self.btn_exec.config(text=tr("adb_terminal_send"))
        self.btn_clear.config(text=tr("adb_terminal_clear"))
