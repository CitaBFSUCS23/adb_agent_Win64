from tkinter import ttk
import threading
from concurrent.futures import ThreadPoolExecutor
from gui.utils import BasePage
from gui.i18n import tr


class DisplayPage(BasePage):
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.info_frame = ttk.LabelFrame(self.frame, text="")
        self.info_frame.pack(fill="x", padx=5, pady=5)
        self.display_info_label = ttk.Label(self.info_frame, text="")
        self.display_info_label.pack(fill="x", padx=5, pady=5)
        
        self.res_frame = ttk.LabelFrame(self.frame, text="")
        self.res_frame.pack(fill="x", padx=5, pady=5)
        
        res_row = ttk.Frame(self.res_frame)
        res_row.pack(fill="x", padx=5, pady=5)
        self.lbl_width = ttk.Label(res_row, text="")
        self.lbl_width.pack(side="left")
        self.res_width_entry = ttk.Entry(res_row, width=10)
        self.res_width_entry.pack(side="left", padx=5)
        self.lbl_height = ttk.Label(res_row, text="")
        self.lbl_height.pack(side="left")
        self.res_height_entry = ttk.Entry(res_row, width=10)
        self.res_height_entry.pack(side="left", padx=5)
        
        res_btn_frame = ttk.Frame(self.res_frame)
        res_btn_frame.pack(fill="x", padx=5, pady=5)
        self.btn_set_res = ttk.Button(res_btn_frame, text="", command=self._set_resolution)
        self.btn_set_res.pack(side="left", padx=3)
        self.btn_reset_res = ttk.Button(res_btn_frame, text="", command=self._reset_resolution)
        self.btn_reset_res.pack(side="left", padx=3)
        
        self.dpi_frame = ttk.LabelFrame(self.frame, text="")
        self.dpi_frame.pack(fill="x", padx=5, pady=5)
        
        dpi_row = ttk.Frame(self.dpi_frame)
        dpi_row.pack(fill="x", padx=5, pady=5)
        self.lbl_dpi = ttk.Label(dpi_row, text="")
        self.lbl_dpi.pack(side="left")
        self.dpi_entry = ttk.Entry(dpi_row, width=10)
        self.dpi_entry.pack(side="left", padx=5)
        
        dpi_btn_frame = ttk.Frame(self.dpi_frame)
        dpi_btn_frame.pack(fill="x", padx=5, pady=5)
        self.btn_set_dpi = ttk.Button(dpi_btn_frame, text="", command=self._set_dpi)
        self.btn_set_dpi.pack(side="left", padx=3)
        self.btn_reset_dpi = ttk.Button(dpi_btn_frame, text="", command=self._reset_dpi)
        self.btn_reset_dpi.pack(side="left", padx=3)
        
        self.refresh_ui()
    
    def refresh_ui(self):
        self.info_frame.config(text=tr("display_info_frame"))
        self.res_frame.config(text=tr("display_resolution_frame"))
        self.lbl_width.config(text=tr("display_width"))
        self.lbl_height.config(text=tr("display_height"))
        self.btn_set_res.config(text=tr("display_set_resolution"))
        self.btn_reset_res.config(text=tr("display_reset_resolution"))
        self.dpi_frame.config(text=tr("display_dpi_frame"))
        self.lbl_dpi.config(text=tr("display_dpi"))
        self.btn_set_dpi.config(text=tr("display_set_dpi"))
        self.btn_reset_dpi.config(text=tr("display_reset_dpi"))
        
    def set_adb_client(self, adb_client):
        self.adb_client = adb_client
        
    def _find_override(self, output, override_key, physical_key):
        lines = output.split("\n")
        override_line = physical_line = None
        for line in lines:
            line = line.strip()
            if override_key in line:
                override_line = line
            elif physical_key in line:
                physical_line = line
        return (override_line or physical_line or "").split(":")[-1].strip()
        
    def load_display_info(self):
        if not self.adb_client or not self.adb_client.current_device:
            return
        threading.Thread(target=self._load_display_info_async, daemon=True).start()

    def _load_display_info_async(self):
        with ThreadPoolExecutor(max_workers=2) as executor:
            wm_size_future = executor.submit(self.adb_client.run_adb_cmd, "shell wm size")
            wm_density_future = executor.submit(self.adb_client.run_adb_cmd, "shell wm density")
            
            output, ok = wm_size_future.result()
            dpi_output, dpi_ok = wm_density_future.result()
        
        data = {}
        if ok and output:
            data["size"] = output
            data["size_str"] = self._find_override(output, "Override size:", "Physical size:")
        if dpi_ok and dpi_output:
            dpi_str = self._find_override(dpi_output, "Override density:", "Physical density:")
            if dpi_str.isdigit():
                data["dpi"] = dpi_str
        
        self.frame.after(0, lambda: self._update_display_info_ui(data))

    def _update_display_info_ui(self, data):
        if "size" in data:
            self.display_info_label.config(text=data["size"])
            if size_str := data.get("size_str"):
                if "x" in size_str:
                    w, h = size_str.split("x")
                    self.res_width_entry.delete(0, "end")
                    self.res_width_entry.insert(0, w.strip())
                    self.res_height_entry.delete(0, "end")
                    self.res_height_entry.insert(0, h.strip())
        if "dpi" in data:
            self.dpi_entry.delete(0, "end")
            self.dpi_entry.insert(0, data["dpi"])
                        
    def _set_resolution(self):
        if (w := self.res_width_entry.get().strip()) and (h := self.res_height_entry.get().strip()):
            self.adb_client.run_adb_cmd(f"shell wm size {w}x{h}")
            self.load_display_info()
            
    def _reset_resolution(self):
        self.adb_client.run_adb_cmd("shell wm size reset")
        self.load_display_info()
        
    def _set_dpi(self):
        if (dpi := self.dpi_entry.get().strip()) and dpi.isdigit():
            self.adb_client.run_adb_cmd(f"shell wm density {dpi}")
            self.load_display_info()
            
    def _reset_dpi(self):
        self.adb_client.run_adb_cmd("shell wm density reset")
        self.load_display_info()
