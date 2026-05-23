from typing import Tuple
from tools import BaseTool


class ADBTool(BaseTool):
    """ADB Tool - Control Android device"""

    @property
    def name(self) -> str:
        return "adb_tool"

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

        # Strip leading "adb " if present — run_adb_cmd already prepends it
        cmd = command.strip()
        if cmd.lower().startswith("adb "):
            cmd = cmd[4:].strip()

        cwd = (context or {}).get("work_dir")
        output, ok = self.adb_client.run_adb_cmd(cmd, cwd=cwd)
        if not output and ok:
            return "(empty output — command may have failed or produced no results)", ok
        return output or "", ok

    def get_prompt_section(self) -> str:
        return (
            f"### {self.name}\n"
            f"- {self.description}\n"
            f"- Commands: shell subcommands (tap, swipe, input, am, pm, settings, etc.)\n"
            f"- NOTE: omit 'adb' prefix — the system adds it automatically"
        )
