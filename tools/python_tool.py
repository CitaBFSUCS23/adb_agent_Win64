import os
import subprocess
import tempfile
from typing import Tuple, Optional, Any, Dict
from tools import BaseTool


class PythonTool(BaseTool):
    """Python Tool - Execute scripts on computer"""

    @property
    def name(self) -> str:
        return "python_tool"

    @property
    def description(self) -> str:
        return "Run Python scripts on Windows computer for data processing"

    @classmethod
    def requires_context(cls) -> bool:
        """PythonTool needs work_dir to resolve relative paths (e.g. skills/)"""
        return True

    @classmethod
    def get_init_params(cls) -> Dict[str, str]:
        """Get required initialization parameters"""
        return {"work_dir": "Working directory for script execution (project root)"}

    def __init__(self, work_dir: str):
        self.work_dir: str = work_dir

    def execute(self, command: str, context: Optional[Dict[str, Any]] = None) -> Tuple[str, bool]:
        """Execute Python code"""
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", encoding="utf-8", delete=False) as f:
                _ = f.write(command)
                temp_path = f.name

            try:
                result = subprocess.run(
                    ["python", temp_path],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=self.work_dir
                )
                output = result.stdout + result.stderr
                success = result.returncode == 0
                return output, success
            finally:
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
        except Exception as e:
            return f"Error executing Python: {e}", False

    def get_prompt_section(self) -> str:
        return (
            f"### {self.name}\n"
            f"- {self.description}\n"
            f"- Runs Python code on Windows host. Available: os, re, json, pathlib, shutil, etc."
        )
