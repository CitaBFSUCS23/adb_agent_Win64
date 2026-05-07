import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog
import threading
import re
import requests
import os
import sys
from gui.utils import BasePage
from gui.i18n import tr

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from tools import BaseTool, discover_tools, load_tools


def _load_skills():
    skills_dir = os.path.join(project_root, "skills")
    skills = {}
    if os.path.exists(skills_dir):
        for filename in os.listdir(skills_dir):
            if filename.endswith(".md"):
                filepath = os.path.join(skills_dir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        skills[filename[:-3]] = f.read()
                except Exception:
                    pass
    return skills


def _build_agent_prompt(tools: dict, skills: dict) -> str:
    """Build Agent system prompt"""
    prompt = """You are an ADB Agent running on Windows. You autonomously complete Android phone tasks.

## Output Format (STRICT - output NOTHING else)

To execute a tool:
THOUGHT: <reasoning>
TOOL: <TOOL_NAME>
COMMAND: <command>

Task complete:
THOUGHT: <summary>
COMPLETE: yes
RESULT: <result summary>

## Critical Rules

1. Output ONE COMMAND per turn
2. Choose the appropriate TOOL based on the task
3. ADB COMMAND must be pure English, NO Chinese characters
4. Device commands use shell prefix: shell ls, shell cat, shell find
5. File transfer: pull /sdcard/file ./local/
6. NEVER use pipe | in ADB COMMAND
7. Decide next step based on OBSERVATION only, never guess
8. If OBSERVATION already has needed info, use it directly
9. On error, analyze and try alternative approach
10. Always focus on the original task goal
11. PYTHON code runs on Windows, use proper path syntax (backslash or raw strings)
12. PYTHON code can use os, shutil, re, json, etc. but no dangerous operations
13. When unsure, use SKILLS below for guidance

## Available Tools

"""

    # Add tools
    for tool_name, tool in tools.items():
        prompt += tool.get_prompt_section() + "\n"

    prompt += "## Available SKILLS (Use as Reference)\n\n"

    # Add skills
    for skill_name, skill_content in skills.items():
        prompt += f"### SKILL: {skill_name}\n{skill_content}\n\n"

    prompt += """## Environment

- Host OS: Windows
- ADB is available for device control
- PYTHON code runs locally on Windows
- Device connected: Will be provided in first user message

## Examples

### Example 1: List photos
THOUGHT: I need to list photos in the camera directory.
TOOL: ADB
COMMAND: shell ls -lt /sdcard/DCIM/Camera/

### Example 2: Pull file
THOUGHT: Now export the first photo.
TOOL: ADB
COMMAND: pull /sdcard/DCIM/Camera/photo.jpg ./exported_photos/

### Example 3: Parse output with Python
THOUGHT: Need to parse the app list to find matching packages.
TOOL: PYTHON
COMMAND:
```python
apps_output = \"\"\"
package:com.android.settings
package:com.example.app
\"\"\"
target = "settings"
packages = [l.replace("package:", "").strip() for l in apps_output.split("\\n") if l.startswith("package:")]
matched = [p for p in packages if target.lower() in p.lower()]
print("Found:", matched)
```

### Example 4: Create directory with Python
THOUGHT: Create export directory if it doesn't exist.
TOOL: PYTHON
COMMAND:
```python
import os
os.makedirs("./exported_photos", exist_ok=True)
print("Directory ready")
```

### Example 5: List apps
THOUGHT: Get all installed apps first.
TOOL: ADB
COMMAND: shell pm list packages
"""
    return prompt

_API_FIELDS = [("agent_api_url", "api_url", 50), ("agent_api_key", "api_key", 50), ("agent_model", "model_name", 30)]

_CHAT_TAGS = {
    "user": {"foreground": "#1a73e8"},
    "agent_thought": {"foreground": "#9334e6"},
    "agent_cmd": {"foreground": "#e37400"},
    "agent_output": {"foreground": "#5f6368"},
    "agent_complete": {"foreground": "#188038"},
    "error": {"foreground": "#d93025"},
    "system": {"foreground": "#5f6368"},
    "pending": {"foreground": "#e37400"},
}

_MEDIA_EXTS = (".jpg", ".png", ".mp4", ".mp3")
_ADB_KEYWORDS = ("shell ", "pull ", "push ", "install ", "uninstall ", "devices", "logcat")
_PHOTO_KEYWORDS = ("photo", "image", "export", "pull", "download", "照片", "图片", "导出", "拉取", "下载")

_RE_THOUGHT = re.compile(r"THOUGHT:\s*(.+?)(?=\nTOOL:|\nCOMMAND:|\nCOMPLETE:|\nRESULT:|$)", re.DOTALL)
_RE_TOOL = re.compile(r"TOOL:\s*(ADB|PYTHON)", re.IGNORECASE)
_RE_COMMAND = re.compile(r"COMMAND:\s*(.+?)(?=\nTHOUGHT:|\nTOOL:|\nCOMPLETE:|\nRESULT:|$)", re.DOTALL)
_RE_COMPLETE = re.compile(r"COMPLETE:\s*(yes|true|1)", re.IGNORECASE)
_RE_RESULT = re.compile(r"RESULT:\s*(.+?)$", re.DOTALL)
_RE_CODE_BLOCK = re.compile(r"^```(?:python|shell|bash)?\s*|\s*```$", re.MULTILINE)
_RE_CHINESE = re.compile(r"[\u4e00-\u9fff]")
_RE_PYTHON_CODE = re.compile(r"```python\s*(.+?)\s*```", re.DOTALL | re.IGNORECASE)


class AgentPage(BasePage):

    def __init__(self, parent):
        super().__init__(parent)
        self._agent_running = False
        self._messages = []
        self._user_action = None
        self._action_event = threading.Event()
        
        # Load skills and initialize tools later (need adb_client)
        self._skills = _load_skills()
        self._tools = {}
        
        self._build_ui()
        self.refresh_ui()

    def _init_tools(self):
        """Initialize tools (must be called after adb_client is set) - now using plugin system!"""
        # Discover all available tools
        tool_classes = discover_tools()
        
        # Prepare context with required parameters
        context = {}
        if self.adb_client:
            context["adb_client"] = self.adb_client
        context["work_dir"] = project_root
        
        # Load and instantiate all tools
        self._tools = load_tools(tool_classes, context)
        
        # Refresh the tools list
        self._refresh_tools_list()

    def _build_ui(self):
        # Top split: 1:1:1 (config: skills: tools)
        top_split = ttk.PanedWindow(self.frame, orient=tk.HORIZONTAL)
        top_split.pack(fill="x", padx=5, pady=5)
        
        # Left: API config
        config_frame = ttk.Frame(top_split)
        top_split.add(config_frame, weight=1)
        
        self._build_api_config(config_frame)
        
        # Middle: Skills
        skills_frame = ttk.Frame(top_split)
        top_split.add(skills_frame, weight=1)
        
        self._build_skills(skills_frame)
        
        # Right: Tools
        tools_frame = ttk.Frame(top_split)
        top_split.add(tools_frame, weight=1)
        
        self._build_tools(tools_frame)
        
        # Bottom: Chat
        self._build_chat()

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
        self.skills_listbox.bind("<Double-Button-1>", lambda e: self._on_skill_double_click())
        
        # Load initial skills
        self._refresh_skills_list()

    def _build_tools(self, parent):
        self.tools_frame = ttk.LabelFrame(parent, text="Tools")
        self.tools_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.tools_listbox = tk.Listbox(self.tools_frame)
        self.tools_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        self.tools_listbox.bind("<Double-Button-1>", lambda e: self._on_tool_double_click())
        
        # Load initial tools (even before device connected)
        self._refresh_tools_list()

    def _refresh_skills_list(self):
        self.skills_listbox.delete(0, "end")
        skills_dir = os.path.join(project_root, "skills")
        if os.path.exists(skills_dir):
            for filename in os.listdir(skills_dir):
                if filename.endswith(".md"):
                    self.skills_listbox.insert("end", filename)

    def _refresh_tools_list(self):
        self.tools_listbox.delete(0, "end")
        tools_dir = os.path.join(project_root, "tools")
        if os.path.exists(tools_dir):
            for filename in os.listdir(tools_dir):
                if filename.endswith(".py") and filename != "__init__.py":
                    self.tools_listbox.insert("end", filename)

    def _show_file_content(self, filepath, title):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            content = f"Error reading file: {str(e)}"
        
        # Create popup window
        popup = tk.Toplevel(self.frame)
        popup.title(title)
        popup.geometry("800x600")
        
        # Create text widget with scrollbar
        text_frame = ttk.Frame(popup)
        text_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        text_widget = scrolledtext.ScrolledText(text_frame, wrap="word")
        text_widget.pack(fill="both", expand=True)
        
        text_widget.insert("1.0", content)
        text_widget.config(state="disabled")  # Make read-only

    def _on_skill_double_click(self):
        if not (sel := self.skills_listbox.curselection()):
            return
        filename = self.skills_listbox.get(sel[0])
        filepath = os.path.join(project_root, "skills", filename)
        if os.path.exists(filepath):
            self._show_file_content(filepath, f"Skill: {filename}")

    def _on_tool_double_click(self):
        if not (sel := self.tools_listbox.curselection()):
            return
        filename = self.tools_listbox.get(sel[0])
        filepath = os.path.join(project_root, "tools", filename)
        if os.path.exists(filepath):
            self._show_file_content(filepath, f"Tool: {filename}")

    def _build_chat(self):
        self.chat_frame = ttk.LabelFrame(self.frame, text="")
        self.chat_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.chat_frame.grid_rowconfigure(0, weight=1)
        self.chat_frame.grid_columnconfigure(0, weight=1)

        self.chat_text = scrolledtext.ScrolledText(self.chat_frame, state="disabled", wrap="word")
        self.chat_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        for tag, cfg in _CHAT_TAGS.items():
            self.chat_text.tag_config(tag, **cfg)

        input_frame = ttk.Frame(self.chat_frame, height=120)
        input_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        input_frame.grid_propagate(False)
        
        left_btn_frame = ttk.Frame(input_frame)
        left_btn_frame.pack(side="left", fill="y", padx=(0, 5))
        self.btn_execute = ttk.Button(left_btn_frame, text="", command=lambda: self._set_action("execute"))
        self.btn_execute.pack(fill="x", pady=2)
        self.btn_reject = ttk.Button(left_btn_frame, text="", command=lambda: self._set_action("reject"))
        self.btn_reject.pack(fill="x", pady=2)
        self.btn_stop = ttk.Button(left_btn_frame, text="", command=self._stop_agent)
        self.btn_stop.pack(fill="x", pady=2)
        self.btn_send = ttk.Button(left_btn_frame, text="", command=self._send_message)
        self.btn_send.pack(fill="x", pady=2)

        self.agent_input = tk.Text(input_frame, height=4, wrap="word")
        self.agent_input.pack(side="right", fill="both", expand=True)
        self.agent_input.bind("<Control-Return>", lambda e: self._send_message())
        self._set_buttons_enabled(False)

    def _set_buttons_enabled(self, enabled):
        state = "normal" if enabled else "disabled"
        for btn in (self.btn_execute, self.btn_reject):
            btn.config(state=state)
    
    def refresh_ui(self):
        self.config_frame.config(text=tr("agent_config_frame"))
        self.chat_frame.config(text=tr("agent_chat_frame"))
        
        for label_key, key, _ in _API_FIELDS:
            self.api_labels[key].config(text=tr(label_key))
        self.btn_test_api.config(text=tr("agent_test_api"))
        self.btn_import_config.config(text=tr("agent_import_config"))
        self.btn_export_config.config(text=tr("agent_export_config"))
        self.btn_execute.config(text=tr("agent_execute"))
        self.btn_reject.config(text=tr("agent_reject"))
        self.btn_stop.config(text=tr("agent_stop"))
        self.btn_send.config(text=tr("agent_send"))

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
            resp = requests.post(api_url, json=payload, headers=headers, timeout=30)
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
                # 默认导出为 KEY=VALUE 格式
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
        
        self._append_chat("user", content + "\n")
        self._messages.append({"role": "user", "content": content})
        
        if not self._tools:
            self._init_tools()
        
        if not self._agent_running:
            self._agent_running = True
            threading.Thread(target=self._agent_loop, daemon=True).start()

    def _stop_agent(self):
        if self._agent_running:
            self._agent_running = False
            self._set_action("stop")
            self._log(tr("agent_stopped"))
        else:
            self._log(tr("agent_not_running"), True)

    def _set_action(self, action):
        self._user_action = action
        self._action_event.set()

    def _append_chat(self, tag, text):
        self.chat_text.config(state="normal")
        self.chat_text.insert("end", text, tag)
        self.chat_text.config(state="disabled")
        self.chat_text.see("end")

    def _log(self, msg, is_error=False):
        self._append_chat("error" if is_error else "system", f"[System] {msg}\n")

    def _agent_loop(self):
        api_url = self.api_entries["api_url"].get().strip()
        api_key = self.api_entries["api_key"].get().strip()
        model_name = self.api_entries["model_name"].get().strip()
        if not api_url:
            self.frame.after(0, lambda: self._log(tr("agent_api_url_required"), True))
            self._agent_running = False
            return
        
        # 确保 URL 正确，自动添加 /chat/completions 后缀
        api_url = api_url.rstrip("/")
        if not api_url.endswith("/chat/completions"):
            api_url = f"{api_url}/chat/completions"

        sys_prompt = _build_agent_prompt(self._tools, self._skills)
        self._messages.insert(0, {"role": "system", "content": sys_prompt})

        try:
            while self._agent_running:
                # Trim history to last ~1000 tokens (approx 20 messages)
                if len(self._messages) > 22:
                    self._messages = [self._messages[0]] + self._messages[-20:]
                
                # Call API
                self.frame.after(0, lambda: self._append_chat("system", "[Agent] Thinking...\n"))
                try:
                    headers = {"Content-Type": "application/json"}
                    if api_key:
                        headers["Authorization"] = f"Bearer {api_key}"
                    payload = {
                        "model": model_name,
                        "messages": self._messages,
                        "temperature": 0.3,
                    }
                    resp = requests.post(api_url, json=payload, headers=headers, timeout=120)
                    resp.raise_for_status()
                    ai_resp = resp.json()["choices"][0]["message"]["content"]
                except Exception as e:
                    self.frame.after(0, lambda e=e: self._log(tr("agent_api_error", error=str(e)), True))
                    break

                self.frame.after(0, lambda: self._append_chat("agent_thought", f"[Agent]\n{ai_resp}\n"))
                self._messages.append({"role": "assistant", "content": ai_resp})

                # Parse
                thought = _RE_THOUGHT.search(ai_resp)
                tool = _RE_TOOL.search(ai_resp)
                cmd = _RE_COMMAND.search(ai_resp)
                complete = _RE_COMPLETE.search(ai_resp)
                result = _RE_RESULT.search(ai_resp)

                if complete:
                    res = result.group(1).strip() if result else ""
                    self.frame.after(0, lambda: self._append_chat("agent_complete", f"[Complete] {res}\n"))
                    break

                if not tool or not cmd:
                    self.frame.after(0, lambda: self._log(tr("agent_parse_error"), True))
                    break

                tool_name = tool.group(1).upper()
                cmd_text = _RE_CODE_BLOCK.sub("", cmd.group(1)).strip()

                if _RE_CHINESE.search(cmd_text) and any(k in cmd_text.lower() for k in _ADB_KEYWORDS):
                    self.frame.after(0, lambda: self._log(tr("agent_chinese_in_cmd"), True))
                    break

                # Execute
                self.frame.after(0, lambda: self._append_chat("agent_cmd", f"[Command] {cmd_text}\n"))
                self._set_buttons_enabled(True)
                
                self._action_event.clear()
                self._user_action = None
                self._action_event.wait()
                
                if self._user_action == "stop":
                    break
                if self._user_action == "reject":
                    self.frame.after(0, lambda: self._log(tr("agent_cmd_rejected")))
                    self._messages.append({"role": "user", "content": "Rejected by user. Please provide an alternative command."})
                    self._set_buttons_enabled(False)
                    continue

                # Run
                self._set_buttons_enabled(False)
                try:
                    if tool_name in self._tools:
                        output, ok = self._tools[tool_name].execute(cmd_text, {"adb_client": self.adb_client, "work_dir": project_root})
                    else:
                        output = f"Unknown tool: {tool_name}"
                        ok = False
                except Exception as e:
                    output = str(e)
                    ok = False

                # Smart observation
                obs = self._smart_observe(output, cmd_text, tool_name)
                
                self.frame.after(0, lambda: self._append_chat("agent_output", f"[Output]\n{output}\n"))
                self._messages.append({"role": "user", "content": f"OBSERVATION:\n{obs}"})
        finally:
            self._agent_running = False
            self.frame.after(0, lambda: self._set_buttons_enabled(False))

    def _smart_observe(self, raw_output, cmd, tool_name):
        lines = raw_output.strip().split("\n")
        if tool_name == "ADB":
            if "ls" in cmd and any(k in cmd for k in _PHOTO_KEYWORDS):
                photo_lines = [l for l in lines if any(ext in l.lower() for ext in _MEDIA_EXTS)]
                if photo_lines:
                    return "\n".join(photo_lines[:20]) + f"\n({len(photo_lines)} files found, pull example: pull /sdcard/DCIM/Camera/xxx.jpg ./local/)"
        if len(raw_output) > 3000:
            return raw_output[:2000] + "\n... (truncated)"
        return raw_output
