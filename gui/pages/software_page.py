import os
from tkinter import ttk, filedialog, messagebox
from gui.utils import BasePage
from gui.i18n import tr


class SoftwarePage(BasePage):

    def __init__(self, parent):
        super().__init__(parent)

        self.app_frame = ttk.LabelFrame(self.frame, text="")
        self.app_frame.pack(fill="both", expand=True, padx=5, pady=5)
        btn_row = ttk.Frame(self.app_frame)
        btn_row.pack(fill="x", padx=5, pady=5)
        self.btn_all = ttk.Button(btn_row, text="", command=lambda f="": self._list_apps(f))
        self.btn_all.pack(side="left", padx=3)
        self.btn_system = ttk.Button(btn_row, text="", command=lambda f="-s": self._list_apps(f))
        self.btn_system.pack(side="left", padx=3)
        self.btn_user = ttk.Button(btn_row, text="", command=lambda f="-3": self._list_apps(f))
        self.btn_user.pack(side="left", padx=3)

        self.app_listbox = ttk.Treeview(self.app_frame, show="tree", height=8)
        self.app_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        self.app_listbox.bind("<<TreeviewSelect>>", self._on_app_select)

        self.action_frame = ttk.LabelFrame(self.frame, text="")
        self.action_frame.pack(fill="x", padx=5, pady=5)
        pkg_row = ttk.Frame(self.action_frame)
        pkg_row.pack(fill="x", padx=5, pady=5)
        self.lbl_pkg = ttk.Label(pkg_row, text="")
        self.lbl_pkg.pack(side="left")
        self.pkg_entry = ttk.Entry(pkg_row)
        self.pkg_entry.pack(side="left", fill="x", expand=True, padx=5)
        self.btn_foreground = ttk.Button(pkg_row, text="", command=self._get_foreground)
        self.btn_foreground.pack(side="left", padx=3)

        ops_row = ttk.Frame(self.action_frame)
        ops_row.pack(fill="x", padx=5, pady=5)
        self.btn_enable = ttk.Button(ops_row, text="", command=lambda a="enable": self._app_action(a))
        self.btn_enable.pack(side="left", padx=3)
        self.btn_disable = ttk.Button(ops_row, text="", command=lambda a="disable": self._app_action(a))
        self.btn_disable.pack(side="left", padx=3)
        self.btn_start = ttk.Button(ops_row, text="", command=lambda a="start": self._app_action(a))
        self.btn_start.pack(side="left", padx=3)
        self.btn_force_stop = ttk.Button(ops_row, text="", command=lambda a="force_stop": self._app_action(a))
        self.btn_force_stop.pack(side="left", padx=3)
        self.btn_export = ttk.Button(ops_row, text="", command=lambda a="export": self._app_action(a))
        self.btn_export.pack(side="left", padx=3)
        self.btn_clear = ttk.Button(ops_row, text="", command=lambda a="clear": self._app_action(a))
        self.btn_clear.pack(side="left", padx=3)
        self.btn_uninstall = ttk.Button(ops_row, text="", command=lambda a="uninstall": self._app_action(a))
        self.btn_uninstall.pack(side="left", padx=3)

        self.install_frame = ttk.LabelFrame(self.frame, text="")
        self.install_frame.pack(fill="x", padx=5, pady=5)
        apk_row = ttk.Frame(self.install_frame)
        apk_row.pack(fill="x", padx=5, pady=5)
        self.btn_select_apk = ttk.Button(apk_row, text="", command=self._select_apk)
        self.btn_select_apk.pack(side="left", padx=3)
        self.apk_path_entry = ttk.Entry(apk_row)
        self.apk_path_entry.pack(side="left", fill="x", expand=True, padx=5)
        inst_btn = ttk.Frame(self.install_frame)
        inst_btn.pack(fill="x", padx=5, pady=5)
        self.btn_install = ttk.Button(inst_btn, text="", command=self._install_apk)
        self.btn_install.pack(side="left", padx=3)
        self.btn_reinstall = ttk.Button(inst_btn, text="", command=lambda: self._install_apk(True))
        self.btn_reinstall.pack(side="left", padx=3)

        self.app_list = []
        self.refresh_ui()

    def refresh_ui(self):
        self.app_frame.config(text=tr("software_frame"))
        self.btn_all.config(text=tr("software_list_all"))
        self.btn_system.config(text=tr("software_list_system"))
        self.btn_user.config(text=tr("software_list_third"))
        self.action_frame.config(text=tr("software_package"))
        self.lbl_pkg.config(text=tr("software_pkg_label"))
        self.btn_foreground.config(text=tr("software_get_foreground"))
        self.btn_enable.config(text=tr("software_enable"))
        self.btn_disable.config(text=tr("software_disable"))
        self.btn_start.config(text=tr("software_start"))
        self.btn_force_stop.config(text=tr("software_force_stop"))
        self.btn_export.config(text=tr("software_export"))
        self.btn_clear.config(text=tr("software_clear"))
        self.btn_uninstall.config(text=tr("software_uninstall"))
        self.install_frame.config(text=tr("software_install_frame"))
        self.btn_select_apk.config(text=tr("software_select_apk"))
        self.btn_install.config(text=tr("software_install"))
        self.btn_reinstall.config(text=tr("software_reinstall"))

    def _require_pkg(self):
        if pkg := self.pkg_entry.get().strip():
            return pkg
        self._log(tr("software_pkg_required"), True)
        return None

    def _list_apps(self, flag):
        if not self.adb_client or not self.adb_client.current_device:
            return
        cmd = f"shell pm list packages {flag}" if flag else "shell pm list packages"
        output, ok = self.adb_client.run_adb_cmd(cmd)
        if ok and output:
            self.app_list = [l.removeprefix("package:").strip() for l in output.split("\n") if l.startswith("package:")]
            self.app_listbox.delete(*self.app_listbox.get_children())
            for app in self.app_list:
                self.app_listbox.insert("", "end", text=app)
            self._log(tr("software_found_apps", count=len(self.app_list)))

    def _on_app_select(self, event):
        if sel := self.app_listbox.selection():
            self._set_entry(self.pkg_entry, self.app_listbox.item(sel[0])["text"])

    def _get_foreground(self):
        if not self.adb_client or not self.adb_client.current_device:
            return
        output, ok = self.adb_client.run_adb_cmd("shell dumpsys activity activities")
        if not (ok and output):
            return
        for line in output.split("\n"):
            s = line.strip()
            if "mResumedActivity" not in s and "mFocusedApp" not in s and "mFocusedWindow" not in s:
                continue
            if "{" in s and "}" in s:
                parts = s.split("{")[1].split("}")[0].split()
                if pkg := next((p.split("/")[0].strip() for p in parts if "/" in p and "." in p), None):
                    self._set_entry(self.pkg_entry, pkg)
                    self._log(tr("software_foreground_package", pkg=pkg))
                    return
            if "package:" in s and (pkg := s.split("package:")[1].split()[0].strip()):
                self._set_entry(self.pkg_entry, pkg)
                self._log(tr("software_foreground_package", pkg=pkg))
                return
        self._log(tr("software_foreground_not_found"), True)

    def _app_action(self, action):
        if not (pkg := self._require_pkg()):
            return
        match action:
            case "enable":
                self._run(f"shell pm enable {pkg}")
            case "disable":
                self._run(f"shell pm disable {pkg}")
            case "start":
                self._run(f"shell monkey -p {pkg} -c android.intent.category.LAUNCHER 1")
            case "force_stop":
                self._run(f"shell am force-stop {pkg}")
            case "clear":
                if messagebox.askyesno(tr("common_ok"), tr("software_clear_confirm")):
                    self._run(f"shell pm clear {pkg}")
            case "uninstall":
                if messagebox.askyesno(tr("common_ok"), tr("software_uninstall_confirm")):
                    self._run(f"uninstall {pkg}")
            case "export":
                self._do_export(pkg)

    def _do_export(self, pkg):
        output, ok = self.adb_client.run_adb_cmd(f"shell pm path {pkg}")
        if not ok or not output:
            return
        apk_path = output.removeprefix("package:").strip()
        if save_path := filedialog.asksaveasfilename(title=tr("software_save_apk_title"), defaultextension=".apk", initialfile=f"{pkg}.apk", filetypes=[(tr("software_apk_file"), "*.apk")]):
            self._run(f"pull {apk_path} {save_path}")

    def _select_apk(self):
        if path := filedialog.askopenfilename(title=tr("software_select_apk_title"), filetypes=[(tr("software_apk_file"), "*.apk")]):
            self._set_entry(self.apk_path_entry, path)

    def _install_apk(self, reinstall=False):
        if not self.adb_client or not self.adb_client.current_device:
            return
        if not (apk_path := self.apk_path_entry.get().strip()):
            self._log(tr("software_please_select_apk"), True)
            return
        if not os.path.exists(apk_path):
            self._log(tr("software_file_not_exists", path=apk_path), True)
            return
        self._run(f"install {'-r ' if reinstall else ''}{apk_path}")
