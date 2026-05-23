from typing import override
from agents import Agent


class ExecutorAgent(Agent):
    """Executes commands via available tools."""

    @property
    @override
    def name(self) -> str:
        return "Executor Agent"

    @property
    @override
    def description(self) -> str:
        return "Executes commands via available tools to complete tasks on the device or host."
