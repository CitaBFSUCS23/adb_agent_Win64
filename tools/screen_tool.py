"""
ScreenTool — captures device screenshot and analyzes it via multimodal LLM.

The Agent calls this tool to "see" the screen.
Flow: ADB screencap → base64 → multimodal LLM (same API as agent) → text description.

Uses the same LLM config as the main agent (api_url, api_key, model_name).
The model must support image input (e.g. qwen-vl-max, gpt-4o, etc.).
"""

from __future__ import annotations

import base64
import subprocess
from pathlib import Path
from typing import Any, Optional

import requests

from tools import BaseTool


class ScreenTool(BaseTool):
    """Screen capture + multimodal analysis. Returns text descriptions with coordinates."""

    @property
    def name(self) -> str:
        return "screen_tool"

    @property
    def description(self) -> str:
        return "Capture device screenshot and analyze screen content via vision AI"

    @classmethod
    def requires_context(cls) -> bool:
        return True

    @classmethod
    def get_init_params(cls) -> dict[str, str]:
        return {"adb_client": "ADBClient for device communication"}

    def __init__(self, adb_client: Any):
        self._adb = adb_client

    # ── Execute ───────────────────────────────────────────────────────────

    def execute(self, command: str, context: Optional[dict] = None) -> tuple[str, bool]:
        ctx = context or {}
        cmd = command.strip().lower() if command else "describe"

        # 1. Capture screen
        screen_b64 = self._capture()
        if not screen_b64:
            return "Failed to capture screenshot. Is device connected?", False

        # 2. Get LLM config from context (same as main agent)
        api_url = ctx.get("api_url", "")
        api_key = ctx.get("api_key", "")
        model_name = ctx.get("model_name", "")
        if not api_url or not model_name:
            return "screen_tool requires api_url and model_name in context", False

        # 3. Build prompt based on command
        if cmd.startswith("find ") or cmd.startswith("locate "):
            target = command.split(" ", 1)[1].strip() if " " in command else "the target"
            prompt = (
                f"Look at this phone screenshot and find: \"{target}\".\n\n"
                "Reply in Chinese with EXACT format:\n"
                "找到了: <description>\n"
                "坐标: (<x>, <y>)\n"
                "置信度: <high/medium/low>\n\n"
                "If not found, reply: 未找到: <reason>"
            )
        elif cmd == "check":
            prompt = (
                "Look at this screenshot. Describe what app/screen is currently shown.\n\n"
                "Reply briefly in Chinese: <app name> - <screen state>\n"
                "Include key interactive elements and their coordinates."
            )
        else:  # describe
            prompt = (
                "Describe this phone screenshot in detail. Include:\n"
                "1. What app/screen is currently shown\n"
                "2. ALL visible UI elements (buttons, icons, text fields, search bars)\n"
                "3. EXACT pixel coordinates of each element as (x, y)\n"
                "4. Current time, status bar info if visible\n\n"
                "Format reply as a clear list in Chinese."
            )

        # 4. Call multimodal LLM with image
        result = self._analyze(screen_b64, prompt, api_url, api_key, model_name)
        if result is None:
            return "Vision model analysis failed. Ensure model supports image input.", False
        return result, True

    # ── Internal: screen capture ──────────────────────────────────────────

    def _capture(self) -> Optional[str]:
        """ADB screencap → base64 PNG string."""
        if not self._adb or not getattr(self._adb, 'current_device', None):
            return None
        try:
            adb = str(Path(__file__).resolve().parent.parent / "dependencies" / "adb.exe")
            result = subprocess.run(
                [adb, "-s", self._adb.current_device, "exec-out", "screencap", "-p"],
                capture_output=True, timeout=10,
            )
            if result.returncode == 0 and result.stdout:
                return base64.b64encode(result.stdout).decode("utf-8")
        except Exception:
            pass
        return None

    # ── Internal: multimodal LLM call ─────────────────────────────────────

    @staticmethod
    def _analyze(image_b64: str, prompt: str,
                 api_url: str, api_key: str, model_name: str) -> Optional[str]:
        """Send image + prompt to multimodal LLM, return text response."""
        try:
            url = api_url.rstrip("/")
            if not url.endswith("/chat/completions"):
                url += "/chat/completions"

            headers = {"Content-Type": "application/json"}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            payload = {
                "model": model_name,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url",
                         "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
                    ],
                }],
                "temperature": 0.2,
            }

            resp = requests.post(url, json=payload, headers=headers, timeout=60)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"[screen_tool] Vision LLM error: {e}")
            return None

    # ── Prompt section ────────────────────────────────────────────────────

    def get_prompt_section(self) -> str:
        return (
            f"### {self.name}\n"
            f"- {self.description}\n"
            f"- Commands: describe (full screen analysis), find <target> (locate element), check (quick screen state)\n"
            f"- ALWAYS look before tapping. Verify after each action."
        )
