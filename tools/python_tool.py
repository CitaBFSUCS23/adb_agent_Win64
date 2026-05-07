import os
import subprocess
import tempfile
from typing import Tuple
from tools import BaseTool


class PythonTool(BaseTool):
    """Python Tool - Execute scripts on computer"""

    @property
    def name(self) -> str:
        return "PYTHON"

    @property
    def description(self) -> str:
        return "Run Python scripts on Windows computer for data processing"

    @classmethod
    def requires_context(cls) -> bool:
        """PythonTool can work without special context (work_dir is optional)"""
        return False

    @classmethod
    def get_init_params(cls) -> dict:
        """Get optional initialization parameters"""
        return {"work_dir": "Working directory for script execution (optional)"}

    def __init__(self, work_dir: str = None):
        self.work_dir = work_dir or os.getcwd()

    def execute(self, command: str, context: dict = None) -> Tuple[str, bool]:
        """Execute Python code"""
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", encoding="utf-8", delete=False) as f:
                f.write(command)
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
        return f"""### Tool: {self.name} (Computer Scripting)
- Purpose: {self.description}
- Syntax: TOOL: {self.name.upper()}, COMMAND: followed by ```python ... ``` code block
- Use cases:
  - Parse complex command output
  - Batch file operations
  - Fuzzy matching for app names
  - Create directories
  - Data analysis and transformation
- Available libraries: os, shutil, re, json, sys, pathlib, etc.
- Security: No network access, no dangerous system operations
"""
