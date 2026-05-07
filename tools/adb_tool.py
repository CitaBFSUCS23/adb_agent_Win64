import re
from typing import Tuple
from tools import BaseTool


class ADBTool(BaseTool):
    """ADB Tool - Control Android device"""

    @property
    def name(self) -> str:
        return "ADB"

    @property
    def description(self) -> str:
        return "Execute commands on connected Android device"

    @classmethod
    def requires_context(cls) -> bool:
        """ADBTool requires adb_client parameter"""
        return True

    @classmethod
    def get_init_params(cls) -> dict:
        """Get required initialization parameters"""
        return {"adb_client": "ADBClient instance for device communication"}

    def __init__(self, adb_client):
        self.adb_client = adb_client

    def execute(self, command: str, context: dict = None) -> Tuple[str, bool]:
        """Execute ADB command"""
        if not self.adb_client:
            return "Error: ADB client not available", False
        
        output, ok = self.adb_client.run_adb_cmd(command)
        return output or "", ok

    def get_prompt_section(self) -> str:
        return f"""### Tool: {self.name} (Phone Control)
- Purpose: {self.description}
- Syntax: TOOL: {self.name.upper()}, COMMAND: <adb subcommand>
- Available commands:
  - shell ls, shell cat, shell find, shell pm list packages
  - shell dumpsys battery, shell screencap, shell input tap, shell input keyevent
  - pull, push, install, uninstall, shell wm size, shell wm density
  - shell settings get/put, shell media volume, etc.
"""

    @staticmethod
    def is_dangerous_command(cmd: str) -> bool:
        """Check if command is dangerous"""
        dangerous_patterns = [
            r"\binstall\b", r"\buninstall\b", r"\bpm clear\b",
            r"\brm\s+-rf\b", r"\bfactory\s+reset\b", r"\bwipe\b",
            r"\breboot\b", r"\bshutdown\b", r"\bformat\b",
        ]
        return any(re.search(p, cmd, re.IGNORECASE) for p in dangerous_patterns)

    @staticmethod
    def has_chinese(text: str) -> bool:
        """Check if text contains Chinese characters"""
        return bool(re.search(r"[\u4e00-\u9fff]", text))
