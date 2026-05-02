import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog
import threading
import re
import requests
from gui.utils import BasePage
from gui.i18n import tr

AGENT_SYSTEM_PROMPT = """You are an ADB Agent running on Windows. You autonomously complete Android phone tasks.

## Output Format (STRICT - output NOTHING else)

To execute ADB command:
THOUGHT: <reasoning>
COMMAND: <adb subcommand, no adb prefix>

Task complete:
THOUGHT: <summary>
COMPLETE: yes
RESULT: <result summary>

## Critical Rules

1. Output ONE COMMAND per turn
2. COMMAND must be pure English adb subcommand, NO Chinese characters
3. Device commands use shell prefix: shell ls, shell cat, shell find
4. File transfer: pull /sdcard/file ./local/
5. NEVER use pipe | in COMMAND
6. Decide next step based on OBSERVATION only, never guess
7. If OBSERVATION already has needed info, use it directly
8. On error, analyze and try alternative approach
9. Always focus on the original task goal

## Environment

- Host OS: Windows
- ADB is available for device control
- Available commands: shell ls, shell cat, shell find, shell pm list packages, shell dumpsys battery, shell screencap, shell input tap, shell input keyevent, pull, push, install, uninstall

## Examples

- List photos: shell ls -lt /sdcard/DCIM/Camera/
- Pull file: pull /sdcard/DCIM/Camera/photo.jpg ./exported_photos/
- List apps: shell pm list packages
- Screenshot: shell screencap -p /sdcard/screenshot.png
- Get battery: shell dumpsys battery
- Tap: shell input tap x y
- Key: shell input keyevent KEYCODE_HOME
- Type: shell input text hello"""

_DANGEROUS_PATTERNS = [
    r"\binstall\b", r"\buninstall\b", r"\bpm clear\b",
    r"\brm\s+-rf\b", r"\bfactory\s+reset\b", r"\bwipe\b",
    r"\breboot\b", r"\bshutdown\b", r"\bformat\b",
]

_API_FIELDS = [("agent_api_url", "api_url", 50), ("agent_api_key", "api_key", 50), ("agent_model", "model_name", 30)]

_CHAT_TAGS = {
    "user": {"foreground": "#1a73e8"},
    "agent_thought": {"foreground": "#9334e6"},
    "agent_cmd": {"foreground": "#e37400"},
    "agent_output": {"foreground": "#5f6368"},
    "agent_complete": {"foreground": "#188038"},
    "error": {"foreground": "#d93025"},
    "system": {"foreground": "#5f6368"},
    "pending": {"foreground": "#e37400", "font": ("Microsoft YaHei", 10, "bold")},
}

_MEDIA_EXTS = (".jpg", ".png", ".mp4", ".mp3")
_ADB_KEYWORDS = ("shell ", "pull ", "push ", "install ", "uninstall ", "devices", "logcat")
_PHOTO_KEYWORDS = ("photo", "image", "export", "pull", "download", "照片", "图片", "导出", "拉取", "下载")

_RE_THOUGHT = re.compile(r"THOUGHT:\s*(.+?)(?=\nCOMMAND:|\nCOMPLETE:|\nRESULT:|$)", re.DOTALL)
_RE_COMMAND = re.compile(r"COMMAND:\s*(.+?)(?=\nTHOUGHT:|\nCOMPLETE:|\nRESULT:|$)", re.DOTALL)
_RE_COMPLETE = re.compile(r"COMPLETE:\s*(yes|true|1)", re.IGNORECASE)
_RE_RESULT = re.compile(r"RESULT:\s*(.+?)$", re.DOTALL)
_RE_CODE_BLOCK = re.compile(r"^```(?:shell|bash)?\s*|\s*```$", re.MULTILINE)
_RE_CHINESE = re.compile(r"[\u4e00-\u9fff]")


class AgentPage(BasePage):

    def __init__(self, parent):
        super().__init__(parent)
        self._agent_running = False
        self._messages = []
        self._user_action = None
        self._action_event = threading.Event()
        self._build_api_config()
        self._build_chat()
        self.refresh_ui()

    def _build_api_config(self):
        self.config_frame = ttk.LabelFrame(self.frame, text="")
        self.config_frame.pack(fill="x", padx=5, pady=5)

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

    def _build_chat(self):
        self.chat_frame = ttk.LabelFrame(self.frame, text="")
        self.chat_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.chat_frame.grid_rowconfigure(0, weight=1)
        self.chat_frame.grid_columnconfigure(0, weight=1)

        self.chat_text = scrolledtext.ScrolledText(self.chat_frame, state="disabled", font=("Microsoft YaHei", 10), wrap="word")
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

        self.agent_input = tk.Text(input_frame, font=("Microsoft YaHei", 10), height=4, wrap="word")
        self.agent_input.pack(side="right", fill="both", expand=True)
        self.agent_input.bind("<Control-Return>", lambda e: self._send_message())
        self._set_buttons_enabled(False)

    def _set_buttons_enabled(self, enabled):
        state = "normal" if enabled else "disabled"
        for btn in (self.btn_execute, self.btn_reject):
            btn.config(state=state)
    
    def refresh_ui(self):
        self.config_frame.config(text=tr("agent_api_config"))
        for label_key, key, _ in _API_FIELDS:
            self.api_labels[key].config(text=tr(label_key))
        self.btn_test_api.config(text=tr("agent_test_api"))
        self.btn_import_config.config(text=tr("agent_import_config"))
        self.btn_export_config.config(text=tr("agent_export_config"))
        self.chat_frame.config(text=tr("agent_chat"))
        self.btn_execute.config(text=tr("agent_execute"))
        self.btn_reject.config(text=tr("agent_reject"))
        self.btn_stop.config(text=tr("agent_stop"))
        self.btn_send.config(text=tr("agent_send"))

    def _set_action(self, action):
        self._user_action = action
        self._action_event.set()

    def _get_api_config(self):
        return {key: entry.get().strip().rstrip("/") if key == "api_url" else entry.get().strip()
                for key, entry in self.api_entries.items()}

    def _set_api_config(self, config):
        for key, entry in self.api_entries.items():
            self._set_entry(entry, config.get(key, ""))

    def _import_config(self):
        if not (path := filedialog.askopenfilename(title=tr("agent_import_config_title"))):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = dict(line.strip().split("=", 1) for line in f if "=" in line and not line.startswith("#"))
            self._set_api_config({k: raw.get(m, "") for k, m in
                                  [("api_url", "API_URL"), ("api_key", "API_KEY"), ("model_name", "MODEL_NAME")]})
            self._chat_log(tr("agent_config_imported"), "agent_complete")
        except Exception as e:
            self._chat_log(tr("agent_config_import_error", error=e), "error")

    def _export_config(self):
        if not (path := filedialog.asksaveasfilename(title=tr("agent_export_config_title"))):
            return
        try:
            c = self._get_api_config()
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"API_URL={c['api_url']}\nAPI_KEY={c['api_key']}\nMODEL_NAME={c['model_name']}\n")
            self._chat_log(tr("agent_config_exported"), "agent_complete")
        except Exception as e:
            self._chat_log(tr("agent_config_export_error", error=e), "error")

    def _chat_log(self, message, tag="system"):
        self.chat_text.config(state="normal")
        self.chat_text.insert("end", message + "\n", tag)
        self.chat_text.see("end")
        self.chat_text.config(state="disabled")

    def _call_api(self, messages, config):
        resp = requests.post(
            f"{config['api_url']}/chat/completions",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {config['api_key']}"},
            json={"model": config["model_name"], "messages": messages, "temperature": 0.1},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    def _parse_response(self, raw):
        result = {"thought": "", "command": "", "complete": False, "result": ""}

        if m := _RE_THOUGHT.search(raw):
            result["thought"] = m.group(1).strip()

        if m := _RE_COMMAND.search(raw):
            cmd = _RE_CODE_BLOCK.sub("", m.group(1).strip())
            result["command"] = cmd.removeprefix("adb ").removeprefix("COMMAND:").strip()

        if _RE_COMPLETE.search(raw):
            result["complete"] = True

        if m := _RE_RESULT.search(raw):
            result["result"] = m.group(1).strip()

        if not result["command"] and not result["complete"]:
            for line in raw.strip().split("\n"):
                s = line.strip()
                if s.startswith("```") or s.startswith("#"):
                    continue
                s = s.removeprefix("adb ").strip()
                if s and not s.startswith(("THOUGHT", "COMPLETE", "RESULT")) and any(kw in s for kw in _ADB_KEYWORDS):
                    result["command"] = s
                    result["thought"] = result["thought"] or "(extracted)"
                    break

        return result

    def _is_dangerous(self, cmd):
        return any(re.search(p, cmd, re.IGNORECASE) for p in _DANGEROUS_PATTERNS)

    def _smart_observation(self, success, output, goal, cmd):
        status = "success" if success else "failed"
        obs = f"[Task goal: {goal}]\n\nOBSERVATION: Command {status}\n"

        if success and output:
            obs += self._analyze_output(output, goal, cmd)

        if not success:
            obs += f"\n[Error output]\n{output}\n"
            if any(kw in output for kw in ("not recognized", "inaccessible or not found")):
                obs += "\n[Hint] Command was incorrectly parsed. Avoid pipe character | in shell commands."
            if any(kw in output.lower() for kw in ("device not found", "no devices")):
                obs += "\n[Hint] Device connection lost. Check USB and USB debugging."
            obs += "\nAnalyze the error and try an alternative approach."

        obs += "\nOutput your next THOUGHT and COMMAND (or COMPLETE)."
        return obs

    def _analyze_output(self, output, goal, cmd):
        obs = ""

        match cmd.split()[0] if cmd.startswith("shell") else "":
            case "ls":
                files = [parts[-1] for line in output.strip().split("\n")
                         if line.startswith("-") and any(ext in line.lower() for ext in _MEDIA_EXTS)
                         and (parts := line.split())]
                if files:
                    obs += f"\n[Analysis] Found {len(files)} files, sorted by time (newest first):\n"
                    obs += "".join(f"  {i}. {f}\n" for i, f in enumerate(files[:20], 1))
                    if len(files) > 20:
                        obs += f"  ... total {len(files)} files\n"
                    if any(kw in goal for kw in _PHOTO_KEYWORDS):
                        n = int(m.group(1)) if (m := re.search(r"(\d+)", goal)) else 10
                        recent = files[:n]
                        dir_path = "/sdcard/" + cmd.split("/sdcard/")[1].split()[0].rstrip("/") if "/sdcard/" in cmd else "/sdcard/DCIM/Camera"
                        obs += f"\n[Hint] The {n} most recent files:\n"
                        obs += "".join(f"  {dir_path}/{f}\n" for f in recent)
                        obs += f"\n[Hint] Use pull command to export, e.g.: pull {dir_path}/{recent[0]} ./exported_photos/\n"

            case "pm":
                if "list packages" in cmd:
                    packages = [l.removeprefix("package:").strip() for l in output.split("\n") if l.startswith("package:")]
                    obs += f"\n[Analysis] Found {len(packages)} installed apps\n"

            case "dumpsys":
                if "battery" in cmd and (m := re.search(r"level:\s*(\d+)", output)):
                    obs += f"\n[Analysis] Battery level: {m.group(1)}%\n"

            case _:
                if output:
                    obs += f"\nOutput:\n{output}\n"

        return obs

    def _wait_for_user_action(self):
        self._action_event.clear()
        self._user_action = None
        self._set_buttons_enabled(True)
        self._action_event.wait()
        self._set_buttons_enabled(False)
        return self._user_action

    def _test_api(self):
        config = self._get_api_config()
        if not all(config.values()):
            self._chat_log(tr("agent_api_config_incomplete"), "error")
            return
        self._chat_log(tr("agent_testing_api"), "system")

        def do_test():
            try:
                result = self._call_api([{"role": "user", "content": "Reply with just: OK"}], config)
                self._chat_log(tr("agent_api_response", response=result[:200]), "agent_output")
                self._chat_log(tr("agent_api_ok"), "agent_complete")
            except Exception as e:
                self._chat_log(tr("agent_api_fail", error=e), "error")

        threading.Thread(target=do_test, daemon=True).start()

    def _send_message(self):
        if self._agent_running:
            self._chat_log(tr("agent_running_please_wait"), "system")
            return
        if not (user_input := self.agent_input.get("1.0", "end").strip()):
            return
        self.agent_input.delete("1.0", "end")

        config = self._get_api_config()
        if not all(config.values()):
            self._chat_log(tr("agent_api_config_incomplete"), "error")
            return
        if not self.adb_client or not self.adb_client.current_device:
            self._chat_log(tr("common_select_device"), "error")
            return

        self._chat_log(tr("agent_user_message", message=user_input), "user")
        self._agent_running = True
        threading.Thread(target=self._run_agent, args=(user_input, config), daemon=True).start()

    def _stop_agent(self):
        self._agent_running = False
        self._action_event.set()
        self._chat_log(tr("agent_stopping"), "system")

    def _run_agent(self, user_goal, config):
        self._messages = [
            {"role": "system", "content": AGENT_SYSTEM_PROMPT},
            {"role": "user", "content": f"Device connected: {self.adb_client.current_device}\n\nUser task: {user_goal}\n\nStart executing. Output your first THOUGHT and COMMAND."},
        ]

        for step in range(1, 21):
            if not self._agent_running:
                self._chat_log(tr("agent_stopped"), "system")
                return

            self._chat_log(tr("agent_step", step=step), "system")

            try:
                raw_response = self._call_api(self._messages, config)
            except Exception as e:
                self._chat_log(tr("agent_api_call_failed", error=e), "error")
                break

            parsed = self._parse_response(raw_response)

            if parsed["thought"]:
                self._chat_log(tr("agent_thought_message", thought=parsed["thought"]), "agent_thought")

            if parsed["complete"]:
                self._chat_log(tr("agent_task_complete"), "agent_complete")
                if parsed["result"]:
                    self._chat_log(tr("agent_result_message", result=parsed["result"]), "agent_complete")
                self._agent_running = False
                return

            if not parsed["command"]:
                self._chat_log(tr("agent_no_valid_command"), "error")
                self._messages += [
                    {"role": "assistant", "content": raw_response},
                    {"role": "user", "content": f"You did not output a valid COMMAND.\nMust output in format:\nTHOUGHT: <reasoning>\nCOMMAND: <adb subcommand>\nCurrent task: {user_goal}\nRe-output now."},
                ]
                continue

            cmd = parsed["command"]

            if _RE_CHINESE.search(cmd):
                self._chat_log(tr("agent_chinese_command_rejected", cmd=cmd), "error")
                self._messages += [
                    {"role": "assistant", "content": raw_response},
                    {"role": "user", "content": f"Your COMMAND contains Chinese characters.\nCOMMAND must be pure English.\nCurrent task: {user_goal}\nRe-output."},
                ]
                continue

            self._chat_log(tr("agent_pending_command", cmd=cmd), "pending")
            if self._is_dangerous(cmd):
                self._chat_log(tr("agent_dangerous_command_warning"), "error")
            self._chat_log(tr("agent_please_confirm"), "system")

            action = self._wait_for_user_action()

            match action:
                case "stop":
                    self._chat_log(tr("agent_user_stopped_task"), "system")
                    self._messages += [
                        {"role": "assistant", "content": raw_response},
                        {"role": "user", "content": f"User stopped the task. Output COMPLETE with a summary.\nCurrent task: {user_goal}"},
                    ]
                    try:
                        p2 = self._parse_response(self._call_api(self._messages, config))
                        if p2["thought"]:
                            self._chat_log(tr("agent_thought_message", thought=p2["thought"]), "agent_thought")
                        if p2["result"]:
                            self._chat_log(tr("agent_result_message", result=p2["result"]), "agent_complete")
                    except Exception:
                        pass
                    self._agent_running = False
                    return

                case "reject":
                    self._chat_log(tr("agent_command_rejected"), "error")
                    self._messages += [
                        {"role": "assistant", "content": raw_response},
                        {"role": "user", "content": f"User rejected this command. Current task: {user_goal}\nConsider alternative approach."},
                    ]
                    continue

                case "execute":
                    output, ok = self.adb_client.run_adb_cmd(cmd)
                    self._messages += [
                        {"role": "assistant", "content": raw_response},
                        {"role": "user", "content": self._smart_observation(ok, output or "", user_goal, cmd)},
                    ]
                    if len(self._messages) > 50:
                        self._messages = [self._messages[0]] + self._messages[-20:]

        self._chat_log(tr("agent_max_steps_reached"), "error")
        self._agent_running = False
