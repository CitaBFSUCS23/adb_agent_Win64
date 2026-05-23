from __future__ import annotations

import importlib
import inspect
import os
import sys
from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseTool(ABC):
    """Base class for all tools."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @classmethod
    @abstractmethod
    def requires_context(cls) -> bool:
        """Does this tool need context params to instantiate?"""
        ...

    @classmethod
    def get_init_params(cls) -> dict[str, str]:
        """Get init param descriptions. Return {param_name: description}."""
        return {}

    @abstractmethod
    def execute(self, command: str, context: Optional[dict] = None) -> tuple[str, bool]: ...

    def get_prompt_section(self) -> str:
        return f"### {self.name}\n- {self.description}"


def discover_tools(tools_dir: Optional[str] = None) -> dict[str, type]:
    """Auto-discover tool classes in tools/ directory. Key = filename (e.g. 'adb_tool')."""
    if tools_dir is None:
        tools_dir = os.path.dirname(os.path.abspath(__file__))
    if tools_dir not in sys.path:
        sys.path.insert(0, os.path.dirname(tools_dir))

    classes: dict[str, type] = {}
    for fn in sorted(os.listdir(tools_dir)):
        if not fn.endswith('.py') or fn == '__init__.py':
            continue
        try:
            mod = importlib.import_module(f'tools.{fn[:-3]}')
            for _name, obj in inspect.getmembers(mod, inspect.isclass):
                if issubclass(obj, BaseTool) and obj is not BaseTool and not inspect.isabstract(obj):
                    classes[fn[:-3]] = obj  # key = filename without .py
        except Exception as e:
            print(f"Warning: Could not load {fn}: {e}")
    return classes


def load_tools(tool_classes: Optional[dict[str, type]] = None,
               context: Optional[dict[str, Any]] = None) -> dict[str, BaseTool]:
    """Instantiate discovered tools with context params."""
    tool_classes = tool_classes or discover_tools()
    ctx = context or {}
    tools: dict[str, BaseTool] = {}

    for tool_name, tool_cls in tool_classes.items():
        try:
            if tool_cls.requires_context():
                params = tool_cls.get_init_params()
                kwargs = {k: ctx[k] for k in params if k in ctx}
                if len(kwargs) >= len(params):
                    tools[tool_name] = tool_cls(**kwargs)
            else:
                tools[tool_name] = tool_cls()
        except Exception as e:
            print(f"Warning: Could not instantiate {tool_name}: {e}")
    return tools
