from typing import Optional, override
from agents import Agent


class LeaderAgent(Agent):
    """Decomposes task → delegates to sub-agents → summarizes."""

    @property
    @override
    def name(self) -> str:
        return "Agent Leader"

    @property
    @override
    def description(self) -> str:
        return "Task decomposition and multi-agent orchestration."

    @property
    @override
    def is_leader(self) -> bool:
        return True

    @override
    def _output_format(self) -> str:
        return (
            '## Format\n'
            'JSON only. Delegate: {"action":"delegate","thought":"...","agent_type":"Agent Name","mission":"task","agent_context":"info"}\n'
            'Done: {"action":"complete","thought":"summary","result":"..."}\n'
            'NEVER execute tools directly — delegate to sub-agents.'
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

    @override
    def _error_hint(self) -> str:
        return (
            '[ERROR] Invalid JSON. Return:\n'
            '{"action":"delegate","thought":"...","agent_type":"...","mission":"...","agent_context":"..."}\n'
            'or {"action":"complete","thought":"...","result":"..."}'
        )
