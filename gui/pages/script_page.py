import tkinter as tk
from tkinter import ttk, scrolledtext
import time
import json
import os
import tempfile
import threading
from PIL import Image, ImageTk
from gui.config import SCRIPTS_DIR
from gui.utils import BasePage
from gui.i18n import tr

def get_script_buttons():
    return [
        {"category": "script_cat_nav", "buttons": [
            {"name_key": "home_key_back", "cmd": "shell input keyevent 4", "template": "shell input keyevent 4", "desc_key": "script_desc_back", "hint_key": "script_hint_back"},
            {"name_key": "home_key_home", "cmd": "shell input keyevent 3", "template": "shell input keyevent 3", "desc_key": "script_desc_home", "hint_key": "script_hint_home"},
            {"name_key": "home_key_recents", "cmd": "shell input keyevent 187", "template": "shell input keyevent 187", "desc_key": "script_desc_recents", "hint_key": "script_hint_recents"},
        ]},
        {"category": "script_cat_volume", "buttons": [
            {"name_key": "home_key_vol_up", "cmd": "shell input keyevent 24", "template": "shell input keyevent 24", "desc_key": "script_desc_vol_up", "hint_key": "script_hint_vol_up"},
            {"name_key": "home_key_vol_down", "cmd": "shell input keyevent 25", "template": "shell input keyevent 25", "desc_key": "script_desc_vol_down", "hint_key": "script_hint_vol_down"},
            {"name_key": "home_key_mute", "cmd": "shell input keyevent 164", "template": "shell input keyevent 164", "desc_key": "script_desc_mute", "hint_key": "script_hint_mute"},
        ]},
        {"category": "script_cat_power", "buttons": [
            {"name_key": "home_key_power", "cmd": "shell input keyevent 26", "template": "shell input keyevent 26", "desc_key": "script_desc_power", "hint_key": "script_hint_power"},
            {"name_key": "home_key_power_long", "cmd": "shell input keyevent --longpress 26", "template": "shell input keyevent --longpress 26", "desc_key": "script_desc_power_long", "hint_key": "script_hint_power_long"},
        ]},
        {"category": "script_cat_touch", "buttons": [
            {"name_key": "script_btn_tap", "cmd": "shell input tap <x> <y>", "template": "shell input tap <x> <y>", "desc_key": "script_desc_tap", "hint_key": "script_hint_tap"},
            {"name_key": "script_btn_longpress", "cmd": "shell input swipe <x> <y> <x> <y> <duration_ms>", "template": "shell input swipe <x> <y> <x> <y> <duration_ms>", "desc_key": "script_desc_longpress", "hint_key": "script_hint_longpress"},
            {"name_key": "script_btn_swipe", "cmd": "shell input swipe <x1> <y1> <x2> <y2> <duration_ms>", "template": "shell input swipe <x1> <y1> <x2> <y2> <duration_ms>", "desc_key": "script_desc_swipe", "hint_key": "script_hint_swipe"},
            {"name_key": "script_btn_input_text", "cmd": "shell input text \"<your_text>\"", "template": "shell input text \"<your_text>\"", "desc_key": "script_desc_input_text", "hint_key": "script_hint_input_text"},
        ]},
        {"category": "script_cat_flow", "buttons": [
            {"name_key": "script_btn_sleep", "cmd": "sleep <seconds>", "template": "sleep <seconds>", "desc_key": "script_desc_sleep", "hint_key": "script_hint_sleep"},
        ]},
    ]


class ScriptPage(BasePage):

    def __init__(self, parent):
        super().__init__(parent)
        self.palette_widgets = []
        self.cat_frames = []
        self.cat_labels = []
        self.last_hint_key = None
        self.captured_coords = []
        self.coord_marker = None
        self.script_running = False
        self.screen_cast_manager = None
        self.coord_picker_window = None
        self._build_ui()
        self.refresh_ui()

    def set_screen_cast_manager(self, manager):
        self.screen_cast_manager = manager

    def _build_ui(self):
        main_split = ttk.PanedWindow(self.frame, orient=tk.HORIZONTAL)
        main_split.pack(fill="both", expand=True, padx=5, pady=5)

        left_frame = ttk.Frame(main_split)
        main_split.add(left_frame, weight=1)

        right_frame = ttk.Frame(main_split)
        main_split.add(right_frame, weight=1)
        
        self.meta_frame = ttk.LabelFrame(left_frame, text="")
        self.meta_frame.pack(fill="x", padx=5, pady=5)
        
        name_row = ttk.Frame(self.meta_frame)
        name_row.pack(fill="x", padx=5, pady=5)
        self.lbl_script_name = ttk.Label(name_row, text="")
        self.lbl_script_name.pack(side="left")
        self.script_name_entry = ttk.Entry(name_row)
        self.script_name_entry.pack(side="left", fill="x", expand=True, padx=5)
        
        self.edit_frame = ttk.LabelFrame(left_frame, text="")
        self.edit_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.script_text = scrolledtext.ScrolledText(
            self.edit_frame, height=12)
        self.script_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.btn_frame = ttk.Frame(self.edit_frame)
        self.btn_frame.pack(fill="x", padx=5, pady=5)
        self.btn_save = ttk.Button(self.btn_frame, text="", command=self._save_script, takefocus=False)
        self.btn_save.pack(side="left", padx=3)
        self.btn_run = ttk.Button(self.btn_frame, text="", command=self._run_script, takefocus=False)
        self.btn_run.pack(side="left", padx=3)
        self.btn_stop = ttk.Button(self.btn_frame, text="", command=self._stop_script, takefocus=False)
        self.btn_stop.pack(side="left", padx=3)
        self.btn_get_coords = ttk.Button(self.btn_frame, text="", command=self._open_coord_picker, takefocus=False)
        self.btn_get_coords.pack(side="left", padx=3)
        
        self.list_frame = ttk.LabelFrame(right_frame, text="")
        self.list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        list_btn_frame = ttk.Frame(self.list_frame)
        list_btn_frame.pack(fill="x", padx=5, pady=5)
        self.btn_load_list = ttk.Button(list_btn_frame, text="", command=self._load_scripts, takefocus=False)
        self.btn_load_list.pack(side="left", padx=3)
        self.btn_delete_selected = ttk.Button(list_btn_frame, text="", command=self._delete_selected, takefocus=False)
        self.btn_delete_selected.pack(side="left", padx=3)
        
        self.script_listbox = tk.Listbox(self.list_frame)
        self.script_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        self.script_listbox.bind("<Double-Button-1>", lambda e: self._on_script_double_click())
        
        self.hint_frame = ttk.LabelFrame(right_frame, text="")
        self.hint_frame.pack(fill="x", padx=5, pady=5)
        self.hint_label = ttk.Label(self.hint_frame, text="", wraplength=400)
        self.hint_label.pack(fill="x", padx=5, pady=5)
        
        self.palette_frame = ttk.LabelFrame(right_frame, text="")
        self.palette_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        palette_scroll_x = ttk.Scrollbar(self.palette_frame, orient=tk.HORIZONTAL)
        palette_scroll_x.pack(side="bottom", fill="x")
        
        palette_scroll_y = ttk.Scrollbar(self.palette_frame, orient=tk.VERTICAL)
        palette_scroll_y.pack(side="right", fill="y")
        
        self.palette_canvas = tk.Canvas(
            self.palette_frame,
            yscrollcommand=palette_scroll_y.set,
            xscrollcommand=palette_scroll_x.set
        )
        self.palette_canvas.pack(side="left", fill="both", expand=True)
        
        palette_scroll_x.config(command=self.palette_canvas.xview)
        palette_scroll_y.config(command=self.palette_canvas.yview)
        
        self.palette_inner = ttk.Frame(self.palette_canvas)
        self.palette_canvas.create_window((0, 0), window=self.palette_inner, anchor="nw", tags="inner")
        
        self._build_palette()
        
        def update_scrollregion(event):
            self.palette_canvas.configure(scrollregion=self.palette_canvas.bbox("all"))
        
        self.palette_inner.bind("<Configure>", update_scrollregion)
        
        self._load_scripts()

    def _build_palette(self):
        self.palette_widgets = []
        self.cat_frames = []
        self.cat_labels = []
        
        script_buttons = get_script_buttons()
        
        for cat in script_buttons:
            cat_label = ttk.Label(self.palette_inner, text="")
            cat_label.pack(fill="x", padx=5, pady=(5, 2))
            self.cat_labels.append((cat_label, cat["category"]))
            
            cat_frame = ttk.Frame(self.palette_inner)
            cat_frame.pack(fill="x", padx=5, pady=2)
            self.cat_frames.append((cat_frame, cat["category"]))
            
            for btn_info in cat["buttons"]:
                btn = ttk.Button(cat_frame, text="", width=15,
                               command=lambda bi=btn_info: self._add_cmd(bi),
                               takefocus=False)
                btn.pack(side="left", padx=2, pady=2)
                
                self.palette_widgets.append((btn, btn_info))

    def _add_cmd(self, btn_info):
        cursor_pos = self.script_text.index(tk.INSERT)
        self.script_text.insert(cursor_pos, "\n" + btn_info["template"])
        new_pos = self.script_text.index(tk.INSERT)
        self.script_text.see(new_pos)
        
        self.last_hint_key = btn_info["hint_key"]
        hint_text = tr(btn_info["hint_key"])
        self.hint_label.config(text=hint_text)

    def _clear_script(self):
        self.script_text.delete("1.0", tk.END)
        self.script_name_entry.delete(0, tk.END)

    def refresh_ui(self):
        self.meta_frame.config(text=tr("script_edit_frame"))
        self.edit_frame.config(text=tr("script_edit_frame"))
        self.list_frame.config(text=tr("script_saved_list"))
        self.hint_frame.config(text=tr("script_hint_frame"))
        self.palette_frame.config(text=tr("script_palette_title"))
        self.lbl_script_name.config(text=tr("script_name_label"))
        self.btn_save.config(text=tr("script_save"))
        self.btn_run.config(text=tr("script_run"))
        self.btn_stop.config(text=tr("script_stop"))
        self.btn_get_coords.config(text=tr("script_btn_get_coords"))
        self.btn_load_list.config(text=tr("script_load_list"))
        self.btn_delete_selected.config(text=tr("script_delete"))
        
        script_buttons = get_script_buttons()
        
        for i, (cat_label, cat_key) in enumerate(self.cat_labels):
            if i < len(script_buttons):
                cat_label.config(text=tr(cat_key))
        
        for i, (btn, btn_info) in enumerate(self.palette_widgets):
            btn.config(text=tr(btn_info["name_key"]))
        
        if self.last_hint_key:
            self.hint_label.config(text=tr(self.last_hint_key))
        else:
            self.hint_label.config(text=tr("script_hint_placeholder"))

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
        for f in SCRIPTS_DIR.glob("*.json"):
            self.script_listbox.insert("end", f.name)

    def _on_script_double_click(self):
        if not (sel := self.script_listbox.curselection()):
            return
        filename = self.script_listbox.get(sel[0])
        with open(SCRIPTS_DIR / filename, "r", encoding="utf-8") as f:
            script = json.load(f)
        self._set_entry(self.script_name_entry, script.get("name", ""))
        self.script_text.delete("1.0", tk.END)
        self.script_text.insert("1.0", script.get("content", ""))

    def _delete_selected(self):
        if not (sel := self.script_listbox.curselection()):
            return
        try:
            filename = self.script_listbox.get(sel[0])
            path = SCRIPTS_DIR / filename
            path.unlink()
            self._log(tr("script_deleted", name=filename))
            self._load_scripts()
        except Exception as e:
            self._log(tr("script_delete_error", error=str(e)), True)

    def _run_script(self):
        if self.script_running:
            self._log(tr("script_already_running"), True)
            return
        
        if not self.adb_client or not self.adb_client.current_device:
            self._log(tr("common_select_device"), True)
            return
        
        content = self.script_text.get("1.0", "end").strip()
        if not content:
            return
        
        self.script_running = True
        threading.Thread(target=self._execute_script, args=(content,), daemon=True).start()

    def _execute_script(self, content):
        lines = [l.strip() for l in content.split("\n") if l.strip() and not l.strip().startswith("#")]
        total = len(lines)
        self._log(tr("script_start_msg", total=total))
        
        for i, line in enumerate(lines, 1):
            if not self.script_running:
                self._log(tr("script_stopped"))
                return
            
            if line.startswith("sleep "):
                try:
                    sec = float(line.split()[1])
                    self._log(tr("script_sleep_msg", i=i, total=total, sec=sec))
                    time.sleep(sec)
                except (ValueError, IndexError):
                    pass
            else:
                self._log(tr("script_cmd_msg", i=i, total=total, cmd=line))
                self.adb_client.run_adb_cmd(line)
        
        if self.script_running:
            self._log(tr("script_complete_msg"))
        self.script_running = False

    def _stop_script(self):
        if self.script_running:
            self.script_running = False
            self._log(tr("script_stopping"))
        else:
            self._log(tr("script_not_running"), True)

    def _capture_screenshot(self):
        phone_file = "/sdcard/.coord_picker_screenshot.png"
        self.adb_client.run_adb("shell", "screencap", "-p", phone_file)
        
        temp_dir = tempfile.gettempdir()
        local_file = os.path.join(temp_dir, "coord_picker_screenshot.png")
        self.adb_client.run_adb("pull", phone_file, local_file)
        self.adb_client.run_adb("shell", "rm", phone_file)
        return local_file

    def _open_coord_picker(self):
        if not self.adb_client or not self.adb_client.current_device:
            self._log(tr("common_select_device"), True)
            return

        if self.coord_picker_window is not None and self.coord_picker_window.winfo_exists():
            self.coord_picker_window.lift()
            self.coord_picker_window.focus_set()
            return
        
        self._log(tr("script_taking_screenshot"))
        threading.Thread(target=self._capture_and_show_picker, daemon=True).start()

    def _capture_and_show_picker(self):
        try:
            local_file = self._capture_screenshot()
            self.frame.after(0, lambda: self._show_coord_picker(local_file))
        except Exception as e:
            self.frame.after(0, lambda: self._log(tr("script_screenshot_failed", error=e), True))

    def _refresh_picker_screenshot(self, canvas, max_w, max_h):
        try:
            local_file = self._capture_screenshot()
            new_img = Image.open(local_file)
            new_phone_w, new_phone_h = new_img.size
            new_scale = min(max_w / new_phone_w, max_h / new_phone_h)
            new_display_w = int(new_phone_w * new_scale)
            new_display_h = int(new_phone_h * new_scale)
            
            new_img_resized = new_img.resize((new_display_w, new_display_h), Image.LANCZOS)
            new_photo = ImageTk.PhotoImage(new_img_resized)
            
            new_offset_x = (max_w - new_display_w) // 2
            new_offset_y = (max_h - new_display_h) // 2
            
            def update_canvas():
                canvas.delete("all")
                canvas.create_image(new_offset_x + new_display_w // 2, new_offset_y + new_display_h // 2, image=new_photo, anchor="center")
                canvas.image = new_photo
                self.captured_coords = []
                self.coord_marker = None
                self.coords_display.config(text="")
            
            self.frame.after(0, update_canvas)
        except Exception as e:
            self.frame.after(0, lambda: self._log(tr("script_screenshot_failed", error=e), True))

    def _show_coord_picker(self, image_path):
        self.captured_coords = []
        self.coord_marker = None
        
        picker_window = tk.Toplevel(self.frame)
        self.coord_picker_window = picker_window
        picker_window.title(tr("script_coord_picker_title"))
        picker_window.geometry("500x700")
        picker_window.transient(self.frame)

        def on_close():
            self.coord_picker_window = None
            picker_window.destroy()
        
        picker_window.protocol("WM_DELETE_WINDOW", on_close)
        
        ttk.Label(picker_window, text=tr("script_coord_picker_info")).pack(fill="x", padx=10, pady=5)
        
        canvas_frame = ttk.Frame(picker_window)
        canvas_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        canvas = tk.Canvas(canvas_frame, bg="gray")
        canvas.pack(fill="both", expand=True)
        
        img = Image.open(image_path)
        phone_w, phone_h = img.size
        
        max_w, max_h = 480, 550
        scale = min(max_w / phone_w, max_h / phone_h)
        display_w = int(phone_w * scale)
        display_h = int(phone_h * scale)
        
        img_resized = img.resize((display_w, display_h), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img_resized)
        
        canvas.config(width=max_w, height=max_h)
        
        offset_x = (max_w - display_w) // 2
        offset_y = (max_h - display_h) // 2
        
        canvas.create_image(offset_x + display_w // 2, offset_y + display_h // 2, image=photo, anchor="center")
        canvas.image = photo
        
        coords_frame = ttk.Frame(picker_window)
        coords_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(coords_frame, text=tr("script_captured_coords")).pack(side="left")
        self.coords_display = ttk.Label(coords_frame, text="", foreground="blue")
        self.coords_display.pack(side="left", padx=5)
        
        btn_frame = ttk.Frame(picker_window)
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        def on_click(event):
            canvas_x = event.x - offset_x
            canvas_y = event.y - offset_y
            
            if canvas_x < 0 or canvas_y < 0 or canvas_x > display_w or canvas_y > display_h:
                return
            
            phone_x = int(canvas_x / scale)
            phone_y = int(canvas_y / scale)
            
            self.captured_coords = [(phone_x, phone_y)]
            
            if self.coord_marker:
                canvas.delete(self.coord_marker)
            self.coord_marker = canvas.create_oval(event.x - 5, event.y - 5, event.x + 5, event.y + 5, fill="red", outline="white", width=2)
            
            self.coords_display.config(text=f"({phone_x}, {phone_y})")
        
        def insert_coords():
            if not self.captured_coords:
                return
            
            x, y = self.captured_coords[0]
            cursor_pos = self.script_text.index(tk.INSERT)
            self.script_text.insert(cursor_pos, f"{x} {y}")
            self.captured_coords = []
            
            if self.coord_marker:
                canvas.delete(self.coord_marker)
            self.coord_marker = None
            self.coords_display.config(text="")
        
        def refresh_screenshot():
            self._log(tr("script_taking_screenshot"))
            threading.Thread(target=self._refresh_picker_screenshot, args=(canvas, max_w, max_h), daemon=True).start()
        
        ttk.Button(btn_frame, text=tr("script_insert_coords"), command=insert_coords, takefocus=False).pack(side="left", padx=5)
        ttk.Button(btn_frame, text=tr("script_clear_coords"), command=self._clear_captured_coords, takefocus=False).pack(side="left", padx=5)
        ttk.Button(btn_frame, text=tr("script_refresh_coords"), command=refresh_screenshot, takefocus=False).pack(side="left", padx=5)
        ttk.Button(btn_frame, text=tr("script_close_picker"), command=on_close, takefocus=False).pack(side="right", padx=5)
        
        canvas.bind("<Button-1>", on_click)

    def _clear_captured_coords(self):
        self.captured_coords = []
        if hasattr(self, 'coord_marker') and self.coord_marker:
            self.coord_marker = None
        if hasattr(self, 'coords_display'):
            self.coords_display.config(text="")
