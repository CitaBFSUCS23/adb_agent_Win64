import tkinter as tk
from tkinter import ttk, scrolledtext
import time
import json
from gui.config import SCRIPTS_DIR
from gui.utils import BasePage
from gui.i18n import tr


class ScriptPage(BasePage):

    def __init__(self, parent):
        super().__init__(parent)

        self.edit_frame = ttk.LabelFrame(self.frame, text="")
        self.edit_frame.pack(fill="both", expand=True, padx=5, pady=5)

        name_row = ttk.Frame(self.edit_frame)
        name_row.pack(fill="x", padx=5, pady=5)
        self.lbl_script_name = ttk.Label(name_row, text="")
        self.lbl_script_name.pack(side="left")
        self.script_name_entry = ttk.Entry(name_row)
        self.script_name_entry.pack(side="left", fill="x", expand=True, padx=5)

        self.script_text = scrolledtext.ScrolledText(self.edit_frame, font=("Consolas", 10), height=8)
        self.script_text.pack(fill="both", expand=True, padx=5, pady=5)

        btn_frame = ttk.Frame(self.edit_frame)
        btn_frame.pack(fill="x", padx=5, pady=5)
        self.btn_save = ttk.Button(btn_frame, text="", command=self._save_script)
        self.btn_save.pack(side="left", padx=3)
        self.btn_run = ttk.Button(btn_frame, text="", command=self._run_script)
        self.btn_run.pack(side="left", padx=3)
        self.btn_load = ttk.Button(btn_frame, text="", command=self._load_scripts)
        self.btn_load.pack(side="left", padx=3)

        self.list_frame = ttk.LabelFrame(self.frame, text="")
        self.list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.script_listbox = tk.Listbox(self.list_frame, font=("Consolas", 10))
        self.script_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        self.script_listbox.bind("<Double-Button-1>", lambda e: self._on_script_double_click())
        
        self.refresh_ui()

    def refresh_ui(self):
        self.edit_frame.config(text=tr("script_edit_frame"))
        self.lbl_script_name.config(text=tr("script_name_label"))
        self.btn_save.config(text=tr("script_save"))
        self.btn_run.config(text=tr("script_run"))
        self.btn_load.config(text=tr("script_load"))
        self.list_frame.config(text=tr("script_saved_list"))

    def _save_script(self):
        name = self.script_name_entry.get().strip()
        content = self.script_text.get("1.0", "end").strip()
        if not name or not content:
            self._log(tr("script_name_content_required"), True)
            return
        path = SCRIPTS_DIR / f"{name}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"name": name, "content": content}, f, ensure_ascii=False, indent=2)
        self._log(tr("script_saved_msg", path=path))
        self._load_scripts()

    def _load_scripts(self):
        self.script_listbox.delete(0, "end")
        for f in sorted(p.name for p in SCRIPTS_DIR.glob("*.json")):
            self.script_listbox.insert("end", f)

    def _on_script_double_click(self):
        if not (sel := self.script_listbox.curselection()):
            return
        with open(SCRIPTS_DIR / self.script_listbox.get(sel[0]), "r", encoding="utf-8") as f:
            script = json.load(f)
        self._set_entry(self.script_name_entry, script.get("name", ""))
        self.script_text.delete("1.0", "end")
        self.script_text.insert("1.0", script.get("content", ""))

    def _run_script(self):
        if not self.adb_client or not self.adb_client.current_device:
            return
        content = self.script_text.get("1.0", "end").strip()
        if not content:
            return
        lines = [l.strip() for l in content.split("\n") if l.strip() and not l.strip().startswith("#")]
        total = len(lines)
        self._log(tr("script_start_msg", total=total))
        for i, line in enumerate(lines, 1):
            if line.startswith("sleep "):
                try:
                    self._log(tr("script_sleep_msg", i=i, total=total, sec=float(line.split()[1])))
                    time.sleep(float(line.split()[1]))
                except (ValueError, IndexError):
                    pass
            else:
                self._log(tr("script_cmd_msg", i=i, total=total, cmd=line))
                self.adb_client.run_adb_cmd(line)
        self._log(tr("script_complete_msg"))
