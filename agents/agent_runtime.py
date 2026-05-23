"""
AgentRunner — thin adapter between UI and Agent.

Only responsibilities:
  1. Wrap LLM API into llm_func (with json_mode toggle)
  2. Create the right agent
  3. Wire callbacks
  4. Call agent.run()
"""

from __future__ import annotations

import threading
from typing import Any, Callable, Optional

import requests

from agents import Agent, discover_agents, LLMFunc
from agents.executor_agent import ExecutorAgent


class AgentRunner:
    """Thin adapter: creates agent + LLM function → calls agent.run()."""

    def __init__(self, tools: dict, work_dir: str,
                 api_url: str, api_key: str, model_name: str,
                 skills: Optional[set[str]] = None):
        self._tools = tools
        self._work_dir = work_dir
        self._skills = skills or set()

        url = api_url.rstrip("/")
        self._api_url = url if url.endswith("/chat/completions") else f"{url}/chat/completions"
        self._api_key = api_key
        self._model = model_name

        self._agent_classes = discover_agents()
        self._running = False
        self._stop = threading.Event()
        self._on_log = None
        self._on_save = None
        self._on_done = None

        # Shared tool context — passed to every tool.execute() call
        self._tool_ctx = {
            "api_url": api_url,
            "api_key": api_key,
            "model_name": model_name,
        }

    def set_callbacks(self, on_log=None, on_save_message=None, on_done=None):
        self._on_log = on_log
        self._on_save = on_save_message
        self._on_done = on_done

    def stop(self):
        self._running = False
        self._stop.set()

    # ── LLM ───────────────────────────────────────────────────────────────

    def _llm(self, messages: list[dict], json_mode: bool = True) -> Optional[str]:
        try:
            headers = {"Content-Type": "application/json"}
            if self._api_key:
                headers["Authorization"] = f"Bearer {self._api_key}"
            body = {"model": self._model, "messages": messages, "temperature": 0.3}
            if json_mode:
                body["response_format"] = {"type": "json_object"}
            resp = requests.post(self._api_url, json=body, headers=headers, timeout=120)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            self._log(f"LLM 调用失败: {e}", True)
            return None

    # ── Helpers ────────────────────────────────────────────────────────────

    def _log(self, msg: str, err: bool = False):
        if self._on_log:
            self._on_log(msg, err)

    def _save(self, role: str, content: str, **kw):
        if self._on_save:
            self._on_save(role, content, **kw)

    def _finish(self):
        self._running = False
        if self._on_done:
            self._on_done()

    def _run_agent(self, agent: Agent, task: str,
                   confirm_cb=None, initial_context=None, **extra):
        """Common runner for all modes."""
        self._running = True
        self._stop.clear()
        try:
            self._log(f"[{agent.name}] Starting...")
            result = agent.run(
                task=task, llm_func=self._llm,
                tools=self._tools, work_dir=self._work_dir,
                skills=sorted(self._skills),
                initial_context=initial_context,
                stop_event=self._stop,
                on_think=lambda msg: self._save("thought", msg),
                on_command=lambda n, c: self._save("command", f"[{n}]\n{c}"),
                on_output=lambda out: self._save("output", out),
                on_complete=lambda res: self._save("complete", res),
                tool_interceptor=confirm_cb,
                llm_raw=lambda msgs: self._llm(msgs, json_mode=False),
                tool_context=self._tool_ctx,
                **extra,
            )
            self._log(f"[{agent.name}] Done: {result}")
        except Exception as e:
            self._log(f"[{agent.name}] Error: {e}", True)
        finally:
            self._finish()

    # ── Public entry points ───────────────────────────────────────────────

    def run_solo(self, task: str, confirm_cb=None, initial_context=None):
        agent = (self._agent_classes.get("Executor Agent") or ExecutorAgent)()
        self._running = True
        self._stop.clear()
        try:
            self._log(f"[{agent.name}] Starting...")
            result = agent.run(
                task=task, llm_func=self._llm,
                tools=self._tools, work_dir=self._work_dir,
                skills=sorted(self._skills),
                initial_context=initial_context,
                stop_event=self._stop,
                on_think=lambda msg: self._save("thought", msg),
                on_command=lambda n, c: None,
                on_output=lambda out: self._save("output", out),
                on_complete=lambda res: self._save("complete", res),
                tool_interceptor=confirm_cb,
                llm_raw=lambda msgs: self._llm(msgs, json_mode=False),
                tool_context=self._tool_ctx,
            )
            self._log(f"[{agent.name}] Done: {result}")
        except Exception as e:
            self._log(f"[{agent.name}] Error: {e}", True)
        finally:
            self._finish()

    def run_corp(self, task: str, chat_only: bool = False, initial_context=None):
        from agents.leader_agent import LeaderAgent
        leader = LeaderAgent()
        self._run_agent(
            leader, task,
            initial_context=initial_context,
            available_agents=self._agent_classes,
            on_log=lambda msg: self._log(msg),
            tool_interceptor=(lambda n, c: "(Chat Only)") if chat_only else None,
        )
