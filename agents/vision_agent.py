"""VisionAgent — screen-first ReAct agent.

Inherits Agent's full ReAct loop. Only customizes the system prompt
to emphasize screen-first workflow. Vision (screenshot + analysis)
is done by screen_tool — a regular tool the agent calls explicitly.
"""

from __future__ import annotations
from typing import Optional, override
from agents import Agent


class VisionAgent(Agent):
    """Screen-first agent: always look before tapping."""

    @property
    @override
    def name(self) -> str:
        return "Vision Agent"

    @property
    @override
    def description(self) -> str:
        return (
            "Controls the device by reading the screen via vision AI. "
            "ALWAYS looks before any tap/swipe/input. "
            "Works like a human: look → think → act → verify."
        )

    @override
    def _output_format(self) -> str:
        return (
            '## Format\n'
            'JSON only. Look+act: {"action":"tool","thought":"what you see, what to do","tool":"NAME","command":"cmd"}\n'
            'Done: {"action":"complete","thought":"summary","result":"..."}\n'
            'Rules: ALWAYS look before tap/swipe/input. Never guess coords. Verify after action. One action per turn.'
        )

    @override
    def _continuation_prompt(self, tool_names: Optional[list[str]] = None,
                             skill_names: Optional[list[str]] = None) -> str:
        parts = [f"You are **{self.name}**. {self.description}"]
        if tool_names:
            parts.append(f"Tools: {', '.join(tool_names)}")
        if skill_names:
            parts.append(f"Skills: {', '.join(skill_names)}")
        parts.append(self._output_format())
        return "\n".join(parts)
