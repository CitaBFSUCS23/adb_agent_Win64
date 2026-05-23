import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import requests
import os
import sys
from datetime import datetime
from typing import Optional, Any, Dict, List, Set
from gui.utils import BasePage
from gui.i18n import tr
from gui.config import HISTORY_DIR, BASE_DIR
from gui.chat_session import ChatSessionManager, ChatMessage

# Add project root to path
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from tools import discover_tools, load_tools
from agents.agent_runtime import AgentRunner
from agents import list_skill_names


def _load_skills():
    return list_skill_names()


_API_FIELDS = [("agent_api_url", "api_url", 50), ("agent_api_key", "api_key", 50), ("agent_model", "model_name", 30)]


class AgentPage(BasePage):

    def __init__(self, parent):
        super().__init__(parent)
        self._agent_running = False
        self._user_action = None
        self._action_event = threading.Event()
        
        # Session management
        self.session_manager = ChatSessionManager(HISTORY_DIR)
        self.current_session = None
        
        # Corp mode
        self._corp_mode_var = tk.BooleanVar(value=False)
        self._corp_runner = None

        # Execution mode checkboxes
        self._always_execute_var = tk.BooleanVar(value=False)
        self._chat_only_var = tk.BooleanVar(value=False)
        
        # Load skills and initialize tools later (need adb_client)
        self._skills = _load_skills()
        self._tools = {}
        
        self._build_ui()
        self.refresh_ui()

    def _init_tools(self):
        """Discover and initialize tools."""
        tool_classes = discover_tools()
        self._tools = load_tools(tool_classes, {
            "adb_client": self.adb_client,
            "work_dir": str(BASE_DIR),
            "api_url": self.api_entries["api_url"].get().strip(),
            "api_key": self.api_entries["api_key"].get().strip(),
            "model_name": self.api_entries["model_name"].get().strip(),
        })
        self._refresh_tools_list()

    def _build_ui(self):
        # Left panel: Session list (relative width)
        left_frame = ttk.Frame(self.frame)
        left_frame.place(x=0, y=0, relwidth=0.18, relheight=1.0)
        self._build_session_list(left_frame)
        
        # Right panel: Main content (fills remaining space)
        right_frame = ttk.Frame(self.frame)
        right_frame.place(relx=0.18, y=0, relwidth=0.82, relheight=1.0)
        
        # Top section: config, skills, tools (equal thirds via pack expand)
        top_frame = ttk.Frame(right_frame)
        top_frame.pack(fill="x", padx=5, pady=5)
        
        config_frame = ttk.Frame(top_frame)
        config_frame.pack(side="left", fill="both", expand=True, padx=2)
        self._build_api_config(config_frame)
        
        skills_frame = ttk.Frame(top_frame)
        skills_frame.pack(side="left", fill="both", expand=True, padx=2)
        self._build_skills(skills_frame)
        
        tools_frame = ttk.Frame(top_frame)
        tools_frame.pack(side="left", fill="both", expand=True, padx=2)
        self._build_tools(tools_frame)
        
        # Bottom: Chat (fills remaining vertical space)
        self._build_chat(right_frame)

    def _build_session_list(self, parent):
        """Build session list panel"""
        self.sessions_frame = ttk.LabelFrame(parent, text="")
        self.sessions_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Top frame for buttons
        btn_frame = ttk.Frame(self.sessions_frame)
        btn_frame.pack(fill="x", padx=5, pady=5)
        
        self.btn_new_session = ttk.Button(btn_frame, text=tr("agent_new_session"), command=self._create_new_session)
        self.btn_new_session.pack(side="left", padx=2, fill="x", expand=True)
        
        # Corp mode checkbox (locked after first message)
        corp_frame = ttk.Frame(self.sessions_frame)
        corp_frame.pack(fill="x", padx=5, pady=(0, 5))
        self.chk_corp_mode = ttk.Checkbutton(
            corp_frame, text=tr("agent_corp_mode"), variable=self._corp_mode_var,
            command=self._on_corp_mode_toggled
        )
        self.chk_corp_mode.pack(side="left")
        
        # Session list container with scrollbar
        list_frame = ttk.Frame(self.sessions_frame)
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.session_scrollbar = ttk.Scrollbar(list_frame, orient="vertical")
        self.session_scrollbar.pack(side="right", fill="y")
        
        self.session_canvas = tk.Canvas(list_frame, yscrollcommand=self.session_scrollbar.set)
        self.session_scrollbar.config(command=self.session_canvas.yview)
        self.session_canvas.pack(side="left", fill="both", expand=True)
        
        self.session_list_container = ttk.Frame(self.session_canvas)
        self._session_list_window = self.session_canvas.create_window((0, 0), window=self.session_list_container, anchor="nw")
        self.session_list_container.bind("<Configure>", lambda e: self.session_canvas.configure(scrollregion=self.session_canvas.bbox("all")))
        self.session_canvas.bind("<Configure>", self._on_session_canvas_configure)
        
        # Session info
        self.session_info_label = ttk.Label(self.sessions_frame, text="")
        self.session_info_label.pack(fill="x", padx=5, pady=5)
        
        # session_id → entry widget mapping
        self._sid_to_entry: Dict[str, ttk.Entry] = {}
        
        # Refresh session list
        self._refresh_session_list()

    def _on_session_canvas_configure(self, event):
        self.session_canvas.itemconfig(self._session_list_window, width=event.width)

    def _build_api_config(self, parent):
        self.config_frame = ttk.LabelFrame(parent, text="")
        self.config_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.api_entries = {}
        self.api_labels = {}
        for i, (label_key, key, width) in enumerate(_API_FIELDS):
            lbl = ttk.Label(self.config_frame, text="")
            lbl.grid(row=i, column=0, sticky="e", padx=5, pady=2)
            self.api_labels[key] = lbl
            entry = ttk.Entry(self.config_frame, width=width)
            entry.grid(row=i, column=1, sticky="ew", padx=5, pady=2)
            self.api_entries[key] = entry

        btn_frame = ttk.Frame(self.config_frame)
        btn_frame.grid(row=len(_API_FIELDS), column=0, columnspan=2, pady=5)
        self.btn_test_api = ttk.Button(btn_frame, text="", command=self._test_api)
        self.btn_test_api.pack(side="left", padx=3)
        self.btn_import_config = ttk.Button(btn_frame, text="", command=self._import_config)
        self.btn_import_config.pack(side="left", padx=3)
        self.btn_export_config = ttk.Button(btn_frame, text="", command=self._export_config)
        self.btn_export_config.pack(side="left", padx=3)
        self.config_frame.columnconfigure(1, weight=1)

    def _build_skills(self, parent):
        self.skills_frame = ttk.LabelFrame(parent, text="Skills")
        self.skills_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.skills_listbox = tk.Listbox(self.skills_frame)
        self.skills_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        self.skills_listbox.bind("<Double-1>", self._on_skill_dblclick)
        
        self._refresh_skills_list()

    def _build_tools(self, parent):
        self.tools_frame = ttk.LabelFrame(parent, text="Tools")
        self.tools_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.tools_listbox = tk.Listbox(self.tools_frame)
        self.tools_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        self.tools_listbox.bind("<Double-1>", self._on_tool_dblclick)
        
        self._refresh_tools_list()

    def _build_chat(self, parent):
        self.chat_frame = ttk.LabelFrame(parent, text="")
        self.chat_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.chat_frame.rowconfigure(0, weight=1)
        self.chat_frame.rowconfigure(1, weight=0)
        self.chat_frame.columnconfigure(0, weight=1)

        # Scrollable chat area
        chat_area = ttk.Frame(self.chat_frame)
        chat_area.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        chat_area.rowconfigure(0, weight=1)
        chat_area.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(chat_area, borderwidth=0, background="#f5f5f5", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self.scrollbar = ttk.Scrollbar(chat_area, orient="vertical", command=self.canvas.yview)
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.chat_container = ttk.Frame(self.canvas, style="Chat.TFrame")
        self._chat_window = self.canvas.create_window((0, 0), window=self.chat_container, anchor="nw", tags="chat_container")

        self.chat_container.bind("<Configure>", self._on_chat_container_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Mouse wheel scrolling
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Store message widgets
        self.message_widgets = []

        # Input area
        input_frame = ttk.Frame(self.chat_frame)
        input_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        input_frame.columnconfigure(1, weight=1)

        left_btn_frame = ttk.Frame(input_frame)
        left_btn_frame.grid(row=0, column=0, sticky="ns", padx=(0, 5))
        self.btn_execute = ttk.Button(left_btn_frame, text="", command=lambda: self._set_action("execute"))
        self.btn_execute.grid(row=0, column=0, sticky="ew", padx=1, pady=1)
        self.btn_reject = ttk.Button(left_btn_frame, text="", command=lambda: self._set_action("reject"))
        self.btn_reject.grid(row=0, column=1, sticky="ew", padx=1, pady=1)
        self.btn_stop = ttk.Button(left_btn_frame, text="", command=self._stop_agent)
        self.btn_stop.grid(row=1, column=0, sticky="ew", padx=1, pady=1)
        self.btn_send = ttk.Button(left_btn_frame, text="", command=self._send_message)
        self.btn_send.grid(row=1, column=1, sticky="ew", padx=1, pady=1)

        self.agent_input = tk.Text(input_frame, height=4, wrap="word", highlightthickness=0, borderwidth=1, relief="solid")
        self.agent_input.grid(row=0, column=1, sticky="nsew")
        self.agent_input.bind("<Control-Return>", lambda e: self._send_message())

        # Right-side checkboxes
        right_chk_frame = ttk.Frame(input_frame)
        right_chk_frame.grid(row=0, column=2, sticky="ns", padx=(5, 0))
        self.chk_always_exec = ttk.Checkbutton(
            right_chk_frame, text="Always Execute", variable=self._always_execute_var)
        self.chk_always_exec.grid(row=0, column=0, sticky="w", pady=1)
        self.chk_chat_only = ttk.Checkbutton(
            right_chk_frame, text="Chat Only", variable=self._chat_only_var)
        self.chk_chat_only.grid(row=1, column=0, sticky="w", pady=1)
        self._set_buttons_enabled(False)

    def _on_chat_container_configure(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        min_width = event.width - 4
        if min_width < 100:
            min_width = 100
        self.canvas.itemconfig(self._chat_window, width=min_width)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _refresh_session_list(self):
        """Refresh session list"""
        for w in self._sid_to_entry.values():
            w.master.destroy()
        self._sid_to_entry.clear()
        
        for session in self.session_manager.list_sessions():
            row = ttk.Frame(self.session_list_container)
            row.pack(fill="x", padx=2, pady=2)
            
            entry = ttk.Entry(row, width=20)
            entry.pack(fill="x", expand=True)
            entry.insert(0, session.title)
            entry.config(state="readonly")
            
            entry.bind("<Button-1>", lambda e, sid=session.session_id: self._load_session(sid))
            entry.bind("<Button-3>", lambda e, s=session: self._on_session_right_click(e, s))
            
            self._sid_to_entry[session.session_id] = entry

    def _on_session_right_click(self, event, session):
        menu = tk.Menu(self.frame, tearoff=0)
        menu.add_command(label=tr("agent_rename_session"), command=lambda: self._start_inplace_edit(session))
        menu.add_separator()
        menu.add_command(label=tr("agent_delete_session"), command=lambda: self._delete_session_with_confirm(session))
        menu.tk_popup(event.x_root, event.y_root)

    def _start_inplace_edit(self, session):
        entry = self._sid_to_entry.get(session.session_id)
        if not entry:
            return
        entry.config(state="normal")
        entry.focus_set()
        entry.select_range(0, tk.END)

        def finish(e=None):
            entry.config(state="readonly")
            t = entry.get().strip()
            if t:
                session.title = t
                self.session_manager.save_session(session)
                if self.current_session and self.current_session.session_id == session.session_id:
                    self.current_session = session
            else:
                entry.delete(0, tk.END)
                entry.insert(0, session.title)
            return "break"

        def cancel(e=None):
            entry.delete(0, tk.END)
            entry.insert(0, session.title)
            entry.config(state="readonly")
            return "break"

        entry.bind("<Return>", finish)
        entry.bind("<Escape>", cancel)
        entry.bind("<FocusOut>", finish)

    def _delete_session_with_confirm(self, session):
        """Delete session with confirmation"""
        # Confirm
        if not messagebox.askyesno(
            title=tr("common_warning"),
            message=tr("agent_delete_session_confirm", title=session.title)
        ):
            return
        
        # Delete
        self.session_manager.delete_session(session.session_id)
        
        # If this was the current session, clear it
        if self.current_session and self.current_session.session_id == session.session_id:
            self.current_session = None
            self._clear_chat_widgets()
            self.session_info_label.config(text="")
        
        self._refresh_session_list()

    def _clear_chat_widgets(self):
        """Clear all chat widgets"""
        for widget in self.message_widgets:
            widget.destroy()
        self.message_widgets = []

    def _update_session_info(self):
        """Update session info label with current language"""
        if not self.current_session:
            return
        
        created_time = datetime.fromisoformat(self.current_session.created_at).strftime("%Y-%m-%d %H:%M")
        updated_time = datetime.fromisoformat(self.current_session.updated_at).strftime("%Y-%m-%d %H:%M")
        info_text = f"{tr('agent_session_title', title=self.current_session.title)}\n"
        info_text += f"{tr('agent_created_at', time=created_time)}\n"
        info_text += f"{tr('agent_updated_at', time=updated_time)}"
        self.session_info_label.config(text=info_text)

    def _load_session(self, session_id):
        """Load a session"""
        session = self.session_manager.get_session(session_id)
        if not session:
            return
        
        self.current_session = session
        
        # Sync corp mode + dependent checkboxes
        self._corp_mode_var.set(session.is_corp_mode)
        if session.is_corp_mode:
            self._always_execute_var.set(True)
            self._chat_only_var.set(False)
            self.chk_always_exec.config(state="disabled")
            self.chk_chat_only.config(state="disabled")
        else:
            self.chk_always_exec.config(state="normal")
            self.chk_chat_only.config(state="normal")
        
        # Clear chat
        self._clear_chat_widgets()
        
        # Load messages
        for idx, msg in enumerate(session.messages):
            self._render_message(msg, idx)
        
        # Update session info
        self._update_session_info()
        
        # Scroll to bottom
        self.canvas.yview_moveto(1.0)

    def _create_new_session(self) -> None:
        """Create a new session"""
        try:
            self.current_session = self.session_manager.create_session(title=tr("agent_new_session_title"))
            self.current_session.is_corp_mode = self._corp_mode_var.get()
            self.session_manager.save_session(self.current_session)
            self._refresh_session_list()
            self._clear_chat_widgets()
            self.session_info_label.config(text=f"{tr('agent_session_title', title=self.current_session.title)}")
        except Exception:
            pass

    def _on_corp_mode_toggled(self):
        """Corp mode — force Always Execute ON + Chat Only OFF."""
        if self._corp_mode_var.get():
            self._always_execute_var.set(True)
            self._chat_only_var.set(False)
            self.chk_always_exec.config(state="disabled")
            self.chk_chat_only.config(state="disabled")
        else:
            self.chk_always_exec.config(state="normal")
            self.chk_chat_only.config(state="normal")

    def _render_message(self, msg: ChatMessage, message_index=None):
        """Render a single message as a chat bubble"""
        # Set up colors based on role
        if msg.role == "user":
            bg_color, fg_color, align = "#1a73e8", "#ffffff", "e"
            role_label = "You"
        elif msg.role == "thought":
            bg_color, fg_color, align = "#9334e6", "#ffffff", "w"
            role_label = "Agent"
        elif msg.role == "command":
            bg_color, fg_color, align = "#e37400", "#ffffff", "w"
            role_label = "Command"
        elif msg.role == "output":
            bg_color, fg_color, align = "#5f6368", "#ffffff", "w"
            role_label = "Output"
        elif msg.role == "complete":
            bg_color, fg_color, align = "#188038", "#ffffff", "w"
            role_label = "Complete"
        else:
            bg_color, fg_color, align = "#e0e0e0", "#333333", "w"
            role_label = "Infomation"

        # Outer frame: full width, aligns bubble left or right
        msg_frame = tk.Frame(self.chat_container, bg="#f5f5f5")
        msg_frame.pack(fill="x", padx=10, pady=4)
        msg_frame.columnconfigure(0, weight=1)

        # Bubble inner frame with background color
        bubble = tk.Frame(msg_frame, bg=bg_color, padx=10, pady=8)
        if align == "e":
            bubble.grid(row=0, column=1, sticky="ne", padx=(40, 0), pady=2)
        else:
            bubble.grid(row=0, column=0, sticky="nw", padx=(0, 40), pady=2)

        # Header row: role label + optional rollback
        header = tk.Frame(bubble, bg=bg_color)
        header.pack(fill="x")

        role_lbl = tk.Label(header, text=role_label, bg=bg_color, fg=fg_color,
                            font=("Arial", 9, "bold"))
        role_lbl.pack(side="left")

        if msg.role == "user" and message_index is not None:
            rollback_btn = tk.Label(header, text="↩", bg=bg_color, fg=fg_color,
                                    font=("Arial", 9, "bold"), cursor="hand2")
            rollback_btn.pack(side="right", padx=(8, 0))
            rollback_btn.bind("<Button-1>", lambda e, idx=message_index: self._rollback_to_message(idx))

        # Content text widget
        text_widget = tk.Text(bubble, wrap="word", bg=bg_color, fg=fg_color,
                              borderwidth=0, highlightthickness=0, padx=0, pady=4,
                              font=("Arial", 10), height=1)
        text_widget.pack(fill="both", expand=True)
        text_widget.insert("end", msg.content)
        text_widget.config(state="disabled")

        # Auto-adjust height based on content
        lines = msg.content.count('\n') + 1
        # Estimate wrapped lines based on average chars per line (~60)
        wrapped = sum((len(line) // 60) + 1 for line in msg.content.split('\n'))
        text_widget.config(height=max(1, min(wrapped, 30)))

        # Store widget reference
        self.message_widgets.append(msg_frame)

        # Scroll to bottom
        self.canvas.yview_moveto(1.0)

    def _rollback_to_message(self, message_index):
        """Rollback conversation to after specified message"""
        if not self.current_session or message_index < 0:
            return
        
        if not messagebox.askyesno(
            title=tr("common_warning"),
            message=tr("agent_rollback")
        ):
            return
        
        # Get the user message content to put back in input
        target_msg = self.current_session.messages[message_index]
        self.agent_input.delete("1.0", "end")
        self.agent_input.insert("1.0", target_msg.content)
        
        # Remove this message and all subsequent messages
        del self.current_session.messages[message_index:]
        self.session_manager.save_session(self.current_session)
        
        # Reload chat
        self._load_session(self.current_session.session_id)

    def _save_message(self, role: str, content: str, **kwargs):
        """Save message to current session."""
        if not self.current_session:
            self._create_new_session()

        # Lock mode checkboxes after first message
        if role == "user" and self.current_session and len(self.current_session.messages) > 0:
            self.chk_corp_mode.config(state="disabled")

        assert self.current_session is not None
        msg = ChatMessage(role=role, content=content, **kwargs)
        self.session_manager.add_message_to_session(self.current_session.session_id, msg)
        message_index = len(self.current_session.messages) - 1
        self._render_message(msg, message_index)

    def _log(self, message: str, is_error: bool = False) -> None:
        """Log system message and save to history"""
        msg_obj = ChatMessage(role="system", content=message)
        if self.current_session:
            self.session_manager.add_message_to_session(self.current_session.session_id, msg_obj)
            self.current_session = self.session_manager.get_session(self.current_session.session_id)
        self._render_message(msg_obj, None)

    def _set_buttons_enabled(self, enabled):
        state = "normal" if enabled else "disabled"
        for btn in (self.btn_execute, self.btn_reject):
            btn.config(state=state)
    
    def refresh_ui(self):
        self.config_frame.config(text=tr("agent_config_frame"))
        self.chat_frame.config(text=tr("agent_chat_frame"))
        self.sessions_frame.config(text=tr("agent_sessions_frame"))
        
        for label_key, key, _ in _API_FIELDS:
            self.api_labels[key].config(text=tr(label_key))
        self.btn_test_api.config(text=tr("agent_test_api"))
        self.btn_import_config.config(text=tr("agent_import_config"))
        self.btn_export_config.config(text=tr("agent_export_config"))
        self.btn_execute.config(text=tr("agent_execute"))
        self.btn_reject.config(text=tr("agent_reject"))
        self.btn_stop.config(text=tr("agent_stop"))
        self.btn_send.config(text=tr("agent_send"))
        self.btn_new_session.config(text=tr("agent_new_session"))
        self.chk_corp_mode.config(text=tr("agent_corp_mode"))
        self.chk_always_exec.config(text=tr("agent_always_execute"))
        self.chk_chat_only.config(text=tr("agent_chat_only"))
        
        # Update session info if a session is loaded
        if self.current_session:
            self._update_session_info()

    def on_device_connected(self):
        self._init_tools()
        self._refresh_skills_list()
        self._refresh_tools_list()

    def _test_api(self):
        api_url = self.api_entries["api_url"].get().strip()
        api_key = self.api_entries["api_key"].get().strip()
        model_name = self.api_entries["model_name"].get().strip()
        if not api_url:
            self._log(tr("agent_api_url_required"), True)
            return
        
        if not model_name:
            self._log("Please enter a model name first.", True)
            return

        self._log(tr("agent_testing_api"))
        threading.Thread(target=self._test_api_thread, args=(api_url, api_key, model_name), daemon=True).start()

    def _test_api_thread(self, url, key, model):
        try:
            api_url = url.rstrip("/")
            if not api_url.endswith("/chat/completions"):
                api_url = f"{api_url}/chat/completions"

            headers = {"Content-Type": "application/json"}
            if key:
                headers["Authorization"] = f"Bearer {key}"

            payload = {"model": model, "messages": [{"role": "user", "content": "hi"}]}
            resp = requests.post(api_url, json=payload, headers=headers, timeout=15)
            resp.raise_for_status()
            self.frame.after(0, lambda: self._log(tr("agent_api_ok")))
        except Exception as e:
            self.frame.after(0, lambda: self._log(f"{tr('agent_api_error', error=str(e))}", True))

    def _import_config(self):
        if not (path := filedialog.askopenfilename(filetypes=[("Config", "*.config"), ("All Files", "*.*")])):
            return
        try:
            cfg = {}
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip()
                        cfg[key] = value
            
            self.api_entries["api_url"].delete(0, tk.END)
            self.api_entries["api_url"].insert(0, cfg.get("API_URL", cfg.get("api_url", "")))
            self.api_entries["api_key"].delete(0, tk.END)
            self.api_entries["api_key"].insert(0, cfg.get("API_KEY", cfg.get("api_key", "")))
            self.api_entries["model_name"].delete(0, tk.END)
            self.api_entries["model_name"].insert(0, cfg.get("MODEL_NAME", cfg.get("model_name", "")))
            self._log(tr("agent_config_imported", path=path))
        except Exception as e:
            self._log(tr("agent_config_import_error", error=str(e)), True)

    def _export_config(self):
        if not (path := filedialog.asksaveasfilename(
            filetypes=[("Config", "*.config"), ("JSON", "*.json"), ("All Files", "*.*")],
            defaultextension=".config"
        )):
            return
        try:
            api_url = self.api_entries["api_url"].get()
            api_key = self.api_entries["api_key"].get()
            model_name = self.api_entries["model_name"].get()
            
            if path.endswith(".json"):
                import json
                cfg = {
                    "api_url": api_url,
                    "api_key": api_key,
                    "model_name": model_name,
                }
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, ensure_ascii=False, indent=2)
            else:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(f"API_URL={api_url}\n")
                    f.write(f"API_KEY={api_key}\n")
                    f.write(f"MODEL_NAME={model_name}\n")
            
            self._log(tr("agent_config_exported", path=path))
        except Exception as e:
            self._log(tr("agent_config_export_error", error=str(e)), True)

    def _send_message(self):
        if not self.adb_client or not self.adb_client.current_device:
            self._log(tr("common_select_device"), True)
            return
        
        content = self.agent_input.get("1.0", "end").strip()
        self.agent_input.delete("1.0", tk.END)
        if not content:
            return
        
        # Save and display user message
        self._save_message("user", content)
        
        if not self._tools:
            self._init_tools()
        
        if not self._agent_running:
            self._agent_running = True
            if self.current_session and self.current_session.is_corp_mode:
                threading.Thread(target=self._run_corp, args=(content,), daemon=True).start()
            else:
                threading.Thread(target=self._run_solo, args=(content,), daemon=True).start()

    # ── Agent execution ──────────────────────────────────────────────────────

    def _run_solo(self, task: str):
        """Run standalone agent with user confirmation."""
        api_url = self.api_entries["api_url"].get().strip()
        api_key = self.api_entries["api_key"].get().strip()
        model_name = self.api_entries["model_name"].get().strip()

        if not api_url:
            self.frame.after(0, lambda: self._log(tr("agent_api_url_required"), True))
            self._agent_running = False
            return

        self._corp_runner = AgentRunner(
            tools=self._tools,
            work_dir=str(BASE_DIR),
            api_url=api_url,
            api_key=api_key,
            model_name=model_name,
            skills=self._skills,
        )

        # Wire callbacks
        self._corp_runner.set_callbacks(
            on_log=lambda msg, err=False: self.frame.after(0, lambda: self._log(msg, err)),
            on_save_message=lambda role, content, **kw: self.frame.after(0, lambda: self._save_message(role, content, **kw)),
            on_done=lambda: self.frame.after(0, lambda: self._on_agent_done()),
        )

        # Provide tool interceptor with user confirmation for solo mode
        def _confirming_exec(tool_name: str, cmd_text: str) -> str:
            self.frame.after(0, lambda: self._save_message("command",
                f"[{tool_name}]\n{cmd_text}"))

            # Chat Only → no execution, return dummy output
            if self._chat_only_var.get():
                self.frame.after(0, lambda: self._save_message("output",
                    "(Chat Only mode — command not executed)"))
                return "(Chat Only — not executed)"

            # Always Execute → skip confirmation
            if not self._always_execute_var.get():
                self.frame.after(0, lambda: self._set_buttons_enabled(True))
                self._action_event.clear()
                self._user_action = None
                self._action_event.wait()

                if self._user_action == "stop":
                    self._agent_running = False
                    return "(stopped by user)"

                if self._user_action == "reject":
                    self.frame.after(0, lambda: self._log(tr("agent_cmd_rejected")))
                    self.frame.after(0, lambda: self._save_message("user",
                        "Rejected by user. Please provide an alternative command."))
                    self.frame.after(0, lambda: self._set_buttons_enabled(False))
                    return "Rejected by user"

            self.frame.after(0, lambda: self._set_buttons_enabled(False))
            try:
                if tool_name in self._tools:
                    output, _ = self._tools[tool_name].execute(cmd_text,
                        {"work_dir": str(BASE_DIR)})
                    return output or "(no output)"
                return f"Unknown tool: {tool_name}"
            except Exception as e:
                return str(e)

        try:
            prior = self.current_session.get_llm_context() if self.current_session else None
            self._corp_runner.run_solo(task, confirm_cb=_confirming_exec, initial_context=prior)
        except Exception as e:
            self.frame.after(0, lambda e=e: self._log(f"Agent error: {e}", True))
        finally:
            self.frame.after(0, self._on_agent_done)

    def _run_corp(self, task: str):
        """Run Agent Leader + sub-agents."""
        api_url = self.api_entries["api_url"].get().strip()
        api_key = self.api_entries["api_key"].get().strip()
        model_name = self.api_entries["model_name"].get().strip()

        if not api_url:
            self.frame.after(0, lambda: self._log(tr("agent_api_url_required"), True))
            self._agent_running = False
            return

        self._corp_runner = AgentRunner(
            tools=self._tools,
            work_dir=str(BASE_DIR),
            api_url=api_url,
            api_key=api_key,
            model_name=model_name,
            skills=self._skills,
        )

        self._corp_runner.set_callbacks(
            on_log=lambda msg, err=False: self.frame.after(0, lambda: self._log(msg, err)),
            on_save_message=lambda role, content, **kw: self.frame.after(0, lambda: self._save_message(role, content, **kw)),
            on_done=lambda: self.frame.after(0, lambda: self._on_agent_done()),
        )

        try:
            prior = self.current_session.get_llm_context() if self.current_session else None
            self._corp_runner.run_corp(task, chat_only=self._chat_only_var.get(), initial_context=prior)
        except Exception as e:
            self.frame.after(0, lambda e=e: self._log(f"Agent Corp error: {e}", True))
        finally:
            self.frame.after(0, self._on_agent_done)

    def _on_agent_done(self):
        """Cleanup after any agent run finishes."""
        self._agent_running = False
        self._corp_runner = None
        self._set_buttons_enabled(False)

    def _stop_agent(self):
        if self._agent_running:
            self._agent_running = False
            if self._corp_runner:
                self._corp_runner.stop()
            self._set_action("stop")
            self._log(tr("agent_stopped"))
        else:
            self._log(tr("agent_not_running"), True)

    def _set_action(self, action):
        self._user_action = action
        self._action_event.set()

    def _refresh_listbox(self, listbox: tk.Listbox, directory: str, extension: str, exclude: Optional[List[str]] = None) -> None:
        """Refresh a listbox with files from a directory"""
        listbox.delete(0, "end")
        if os.path.exists(directory):
            for filename in os.listdir(directory):
                if filename.endswith(extension) and (not exclude or filename not in exclude):
                    listbox.insert("end", filename)

    def _refresh_skills_list(self) -> None:
        self._refresh_listbox(self.skills_listbox, str(BASE_DIR / "skills"), ".md")

    def _refresh_tools_list(self) -> None:
        self._refresh_listbox(self.tools_listbox, str(BASE_DIR / "tools"), ".py", exclude=["__init__.py"])

    # ── Double-click preview ─────────────────────────────────────────────

    def _on_skill_dblclick(self, event):
        sel = self.skills_listbox.curselection()
        if not sel:
            return
        name = self.skills_listbox.get(sel[0])
        path = BASE_DIR / "skills" / name
        if path.exists():
            self._show_preview(name, path.read_text(encoding="utf-8"))

    def _on_tool_dblclick(self, event):
        sel = self.tools_listbox.curselection()
        if not sel:
            return
        name = self.tools_listbox.get(sel[0])
        path = BASE_DIR / "tools" / name
        if path.exists():
            self._show_preview(name, path.read_text(encoding="utf-8"))

    def _show_preview(self, title: str, content: str):
        win = tk.Toplevel(self.frame)
        win.title(title)
        win.geometry("600x500")
        
        text = tk.Text(win, wrap="word", padx=8, pady=8)
        scroll = ttk.Scrollbar(win, command=text.yview)
        text.config(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        text.pack(fill="both", expand=True)
        
        text.insert("1.0", content)
        text.config(state="disabled")
