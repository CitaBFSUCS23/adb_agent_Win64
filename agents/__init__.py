"""
Unified Agent Architecture — single Agent class, two modes.

Agent(is_leader=False) — ReAct loop: tool → observe → repeat → complete
Agent(is_leader=True)  — decompose → delegate to sub-agents → summarize

Features preserved:
  - ReAct loop with loop detection
  - Context compression (every 20 rounds)
  - JSON output format (API-level enforcement)
  - Lazy tool/skill detail injection (names only in prompt, details on demand)
  - Skill & Tool routing
  - Leader delegation + auto-delegate fallback
  - VisionAgent screenshot injection hook
  - Dynamic discovery
"""

from __future__ import annotations

import importlib
import inspect
import json
import os
import re
import sys
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Optional

LLMFunc = Callable[[list[dict[str, object]]], Optional[str]]


# ═══════════════════════════════════════════════════════════════════════════════
# JSON parser
# ═══════════════════════════════════════════════════════════════════════════════

_CB = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def parse_json(text: str) -> dict[str, Optional[str]]:
    """Parse LLM response as JSON. Returns normalized dict with all standard keys."""
    cleaned = _CB.sub("", text).strip()
    for attempt in (cleaned, cleaned[cleaned.find("{"):cleaned.rfind("}") + 1]
                    if "{" in cleaned and "}" in cleaned else ""):
        if not attempt:
            continue
        try:
            obj = json.loads(attempt)
            if isinstance(obj, dict):
                return _norm(obj)
        except json.JSONDecodeError:
            pass
    return _empty()


def _norm(o: dict) -> dict[str, Optional[str]]:
    a = o.get("action", "")
    r = {
        "action": a, "thought": o.get("thought"),
        "tool": o.get("tool") or o.get("tool_name"),
        "command": o.get("command") or o.get("cmd"),
        "complete": "yes" if a == "complete" else None,
        "result": o.get("result"),
        "handoff": o.get("handoff") or o.get("target"),
        "context": o.get("context") or o.get("handoff_context"),
        "agent_type": o.get("agent_type") or o.get("type"),
        "mission": o.get("mission"),
        "agent_context": o.get("agent_context") or o.get("delegate_context"),
    }
    for k, v in r.items():
        if v is not None and not isinstance(v, str):
            r[k] = str(v)
    return r


def _empty() -> dict[str, Optional[str]]:
    return {k: None for k in (
        "action", "thought", "tool", "command", "complete",
        "result", "handoff", "context", "agent_type", "mission", "agent_context")}


# ═══════════════════════════════════════════════════════════════════════════════
# Skill loader (lazy — only loads content when requested)
# ═══════════════════════════════════════════════════════════════════════════════

_SKILLS_DIR: Optional[Path] = None


def _skills_dir() -> Path:
    global _SKILLS_DIR
    if _SKILLS_DIR is None:
        _SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"
    return _SKILLS_DIR


def load_skill_content(name: str) -> Optional[str]:
    """Load skill .md content by name. Returns None if not found."""
    p = _skills_dir() / f"{name}.md"
    try:
        return p.read_text(encoding="utf-8") if p.exists() else None
    except Exception:
        return None


def list_skill_names() -> list[str]:
    """List available skill names."""
    d = _skills_dir()
    if not d.exists():
        return []
    return sorted(f.stem for f in d.iterdir() if f.suffix == ".md")


# ═══════════════════════════════════════════════════════════════════════════════
# Agent
# ═══════════════════════════════════════════════════════════════════════════════

class Agent(ABC):
    """Unified agent. Subclasses provide identity + output format."""

    COMPRESS_EVERY = 20
    ABS_MAX        = 50
    MAX_LOOP       = 3

    # ── Identity (subclasses override) ───────────────────────────────────

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @property
    def is_leader(self) -> bool:
        return False

    # ── Output format (subclasses may override) ──────────────────────────

    def _output_format(self) -> str:
        return (
            '## Format\n'
            'JSON only. Tool: {"action":"tool","thought":"...","tool":"NAME","command":"cmd"}\n'
            'Done: {"action":"complete","thought":"...","result":"..."}\n'
            'Handoff: {"action":"handoff","thought":"...","handoff":"Agent","context":"..."}\n'
            'One action per turn.'
        )

    def _continuation_prompt(self, tool_names: Optional[list[str]] = None,
                             skill_names: Optional[list[str]] = None) -> str:
        parts = [f"You are **{self.name}**. {self.description}"]
        if tool_names:
            parts.append(f"Tools: {', '.join(tool_names)}")
        if skill_names:
            parts.append(f"Skills: {', '.join(skill_names)}")
        parts.append(self._output_format())
        return "\n".join(parts)

    def _error_hint(self) -> str:
        return (
            '[ERROR] Invalid JSON. Return:\n'
            '{"action":"tool","thought":"...","tool":"...","command":"..."}\n'
            'or {"action":"complete","thought":"...","result":"..."}'
        )

    # ── Prompt builder (lazy: names only) ────────────────────────────────

    def _build_prompt(self, tools: Optional[dict], skills: Optional[list[str]],
                      handoff_targets: Optional[list[str]] = None,
                      extra: str = "") -> str:
        parts = [f"You are **{self.name}**. {self.description}"]
        if tools:
            parts.append(f"Tools: {', '.join(tools.keys())}")
        if skills:
            parts.append(f"Skills: {', '.join(skills)}")
        parts.append(self._output_format())
        if handoff_targets:
            parts.append(f"Handoff: {', '.join(handoff_targets)}")
        if extra:
            parts.append(extra)
        return "\n".join(parts)

    # ── Context helpers ──────────────────────────────────────────────────

    @staticmethod
    def _tool_names(tools: Optional[dict]) -> list[str]:
        return sorted(tools.keys()) if tools else []

    def _init_ctx(self, task: str, mission: str, parent_context: str,
                  tools: Optional[dict], skills: Optional[list[str]],
                  handoff_targets: Optional[list[str]], extra: str = "",
                  initial_context: Optional[list] = None) -> list[dict]:
        tnames = self._tool_names(tools)
        snames = skills or []

        if initial_context:
            sys = self._continuation_prompt(tnames, snames) + extra
            return [{"role": "system", "content": sys},
                    *initial_context,
                    {"role": "user", "content": task}]

        sys = self._build_prompt(tools, snames, handoff_targets, extra)
        user_parts = [f"Task: {task}"]
        if mission:
            user_parts.append(f"Mission: {mission}")
        if parent_context:
            user_parts.append(f"Context: {parent_context}")
        return [{"role": "system", "content": sys},
                {"role": "user", "content": " | ".join(user_parts)}]

    @staticmethod
    def _compress(ctx: list[dict], llm: LLMFunc, keep: int = 6) -> list[dict]:
        if len(ctx) <= keep + 1:
            return ctx
        sys = [ctx[0]] if ctx and ctx[0]["role"] == "system" else []
        old = ctx[len(sys):-keep]
        if not old:
            return ctx
        text = "\n---\n".join(f"[{m['role']}] {m['content']}" for m in old)
        prompt = f"Summarize in ≤300 tokens. Keep: goal, steps, state, findings.\n\n{text}"
        summary = (llm([{"role": "user", "content": prompt}]) or text).strip()
        return sys + [{"role": "user", "content": f"[History]\n{summary}"}] + ctx[-keep:]

    # ── Tool execution ───────────────────────────────────────────────────

    @staticmethod
    def _exec_tool(name: str, cmd: str, tools: Optional[dict],
                   work_dir: str, tool_ctx: Optional[dict] = None) -> str:
        if not tools or name not in tools:
            return f"Unknown tool: {name}"
        try:
            ctx = {"work_dir": work_dir}
            if tool_ctx:
                ctx.update(tool_ctx)
            out, _ = tools[name].execute(cmd, ctx)
            return out or "(no output)"
        except Exception as e:
            return f"[Tool Error] {e}"

    # ── Lazy detail injection ────────────────────────────────────────────

    @staticmethod
    def _inject_tool_detail(tool_name: str, tools: Optional[dict]) -> str:
        """Return tool's full prompt section, or empty if unknown."""
        if tools and tool_name in tools:
            return tools[tool_name].get_prompt_section()
        return ""

    @staticmethod
    def _inject_skill_detail(skill_name: str) -> str:
        """Return skill .md content, or empty if not found."""
        content = load_skill_content(skill_name)
        return content or ""

    def _build_result_msg(self, tool_name: str, cmd: str, out: str,
                          tools: Optional[dict], skills: Optional[list[str]]) -> str:
        """Build user message with lazy-injected tool/skill details + result."""
        parts: list[str] = []

        # Inject tool detail (only first time this tool is used in this run)
        detail = self._inject_tool_detail(tool_name, tools)
        if detail:
            parts.append(f"[{tool_name} reference]\n{detail}")

        # Check if command references a skill name
        if skills:
            cmd_lower = cmd.lower()
            for s in skills:
                if s.lower() in cmd_lower:
                    sd = self._inject_skill_detail(s)
                    if sd:
                        parts.append(f"[Skill: {s}]\n{sd}")

        parts.append(f"[{tool_name} result]\n{out}")
        return "\n\n".join(parts)

    # ── Vision hook ──────────────────────────────────────────────────────

    def _inject_screenshot(self, ctx: list[dict]) -> None:
        """Override in VisionAgent to inject screen capture."""
        pass

    # ── Main loop ────────────────────────────────────────────────────────

    def run(self,
            task: str,
            llm_func: LLMFunc,
            tools: Optional[dict[str, Any]] = None,
            work_dir: str = "",
            original_task: str = "",
            mission: str = "",
            parent_context: str = "",
            skills: Optional[list[str]] = None,
            handoff_targets: Optional[list[str]] = None,
            initial_context: Optional[list[dict[str, str]]] = None,
            stop_event: Optional[threading.Event] = None,
            on_think: Optional[Callable[[str], None]] = None,
            on_command: Optional[Callable[[str, str], None]] = None,
            on_output: Optional[Callable[[str], None]] = None,
            on_complete: Optional[Callable[[str], None]] = None,
            tool_interceptor: Optional[Callable[[str, str], str]] = None,
            llm_raw: Optional[LLMFunc] = None,
            available_agents: Optional[dict[str, type]] = None,
            on_log: Optional[Callable[[str], None]] = None,
            tool_context: Optional[dict[str, Any]] = None,
            **kwargs) -> str:

        if not original_task:
            original_task = task
        _raw = llm_raw or llm_func

        # Track which tool/skill details have been injected (avoid re-injecting)
        _injected_tools: set[str] = set()
        _injected_skills: set[str] = set()

        # Build extra section for leader
        extra = ""
        if self.is_leader and available_agents is None:
            available_agents = discover_agents()
        if self.is_leader and available_agents:
            summaries = []
            for cls in available_agents.values():
                try:
                    summaries.append(f"- **{cls().name}**: {cls().description}")
                except Exception:
                    pass
            extra = "\n\n## Sub-Agents\n" + "\n".join(summaries)

        ctx = self._init_ctx(task, mission, parent_context, tools, skills,
                             handoff_targets, extra, initial_context)

        iteration = 0
        recent: list[tuple] = []
        has_acted = False

        while True:
            iteration += 1
            if iteration > self.ABS_MAX:
                return self._done(on_complete, "Max iterations reached")
            if stop_event and stop_event.is_set():
                return "Interrupted"
            if iteration > 1 and iteration % self.COMPRESS_EVERY == 0:
                ctx = self._compress(ctx, _raw)

            self._inject_screenshot(ctx)

            resp = llm_func(ctx)
            if not resp:
                return "LLM call failed"
            ctx.append({"role": "assistant", "content": resp})

            p = parse_json(resp)
            if on_think:
                on_think(f"[{self.name}] {p.get('thought') or resp[:200]}")

            # ── COMPLETE ─────────────────────────────────────────────────
            if p["complete"]:
                if not has_acted and iteration <= 2:
                    ctx.append({"role": "user", "content":
                        f"[ERROR] Execute at least one action first.\n{self._error_hint()}"})
                    continue
                result = self._summarize(p["result"] or "Done", _raw)
                return self._done(on_complete, result)

            # ── HANDOFF (react mode) ─────────────────────────────────────
            if p["handoff"] and not self.is_leader:
                return self._done(on_complete, f"Handoff → {p['handoff']}")

            # ── TOOL (react mode) ────────────────────────────────────────
            if p["tool"] and p["command"] and not self.is_leader:
                tool_name, cmd = p["tool"], p["command"].strip()
                # loop detection
                key = (tool_name, cmd)
                recent.append(key)
                if len(recent) >= self.MAX_LOOP and len(set(recent[-self.MAX_LOOP:])) == 1:
                    ctx.append({"role": "user", "content":
                        f"[LOOP] Same command {self.MAX_LOOP}x. Try differently or complete."})
                    recent.clear()
                    continue
                if on_command:
                    on_command(tool_name, cmd)
                has_acted = True
                out = (tool_interceptor(tool_name, cmd)
                       if tool_interceptor
                       else self._exec_tool(tool_name, cmd, tools, work_dir, tool_context))
                if on_output:
                    on_output(out)
                # Lazy inject: tool detail (first use only) + skill detail (if referenced)
                msg_parts: list[str] = []
                if tool_name not in _injected_tools:
                    detail = self._inject_tool_detail(tool_name, tools)
                    if detail:
                        msg_parts.append(f"[{tool_name} reference]\n{detail}")
                    _injected_tools.add(tool_name)
                if skills:
                    cmd_lower = cmd.lower()
                    for s in skills:
                        if s.lower() in cmd_lower and s not in _injected_skills:
                            sd = self._inject_skill_detail(s)
                            if sd:
                                msg_parts.append(f"[Skill: {s}]\n{sd}")
                            _injected_skills.add(s)
                msg_parts.append(f"[{tool_name} result]\n{out}")
                ctx.append({"role": "user", "content": "\n\n".join(msg_parts)})
                continue

            # ── DELEGATE (leader mode) ───────────────────────────────────
            if self.is_leader and p["action"] in ("delegate", "handoff") or p["handoff"] and self.is_leader:
                sub = self._resolve_sub(p, resp, task, available_agents or {})
                if sub is None:
                    ctx.append({"role": "user", "content":
                        f"[ERROR] Unknown agent. Available: {', '.join((available_agents or {}).keys())}"})
                    continue
                has_acted = True
                if on_log:
                    on_log(f"[{self.name}] → {sub.name}")
                sub_result = sub.run(
                    task=task, llm_func=llm_func, tools=tools, work_dir=work_dir,
                    original_task=task, skills=skills,
                    mission=getattr(sub, '_mission', ''),
                    parent_context=getattr(sub, '_ctx', ''),
                    stop_event=stop_event,
                    on_think=on_think, on_command=on_command, on_output=on_output,
                    tool_interceptor=tool_interceptor, llm_raw=_raw,
                    available_agents=available_agents, on_log=on_log,
                    tool_context=tool_context,
                )
                tag = "" if sub_result.startswith("[HANDOFF]") else " Result"
                ctx.append({"role": "user", "content": f"[{sub.name}{tag}]\n{sub_result}"})
                continue

            # ── Leader auto-delegate when trying to use tools directly ───
            if self.is_leader and p["tool"] and p["command"] and available_agents:
                first_cls = next(iter(available_agents.values()))
                sub = first_cls()
                sub._mission = p["command"]
                sub._ctx = resp
                has_acted = True
                if on_log:
                    on_log(f"[{self.name}] Auto-delegate → {sub.name}")
                sub_result = sub.run(
                    task=task, llm_func=llm_func, tools=tools, work_dir=work_dir,
                    original_task=task, skills=skills,
                    mission=sub._mission, parent_context=sub._ctx,
                    stop_event=stop_event,
                    on_think=on_think, on_command=on_command, on_output=on_output,
                    tool_interceptor=tool_interceptor, llm_raw=_raw,
                    available_agents=available_agents, on_log=on_log,
                    tool_context=tool_context,
                )
                ctx.append({"role": "user", "content": f"[{sub.name} Result]\n{sub_result}"})
                continue

            # ── Parse failure ────────────────────────────────────────────
            ctx.append({"role": "user", "content": self._error_hint()})

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _summarize(text: str, llm: LLMFunc) -> str:
        if not text or len(text) < 200:
            return text
        prompt = f"Summarize in ≤300 tokens. Keep: goal, steps, state, findings.\n\n{text}"
        return (llm([{"role": "user", "content": prompt}]) or text).strip()

    @staticmethod
    def _done(on_complete: Optional[Callable], result: str) -> str:
        if on_complete:
            on_complete(result)
        return result

    def _resolve_sub(self, parsed: dict, raw: str, fallback_mission: str,
                     available: dict[str, type]) -> Optional[Agent]:
        agent_type = parsed.get("agent_type") or parsed.get("handoff")
        if not agent_type or agent_type not in available:
            for name in available:
                if name.lower() in (raw or "").lower():
                    agent_type = name
                    break
        if not agent_type or agent_type not in available:
            return None
        agent = available[agent_type]()
        agent._mission = parsed.get("mission") or fallback_mission
        agent._ctx = parsed.get("agent_context") or parsed.get("context") or ""
        return agent


# ═══════════════════════════════════════════════════════════════════════════════
# Dynamic discovery
# ═══════════════════════════════════════════════════════════════════════════════

_CACHE: Optional[dict[str, type]] = None


def discover_agents(agents_dir: Optional[str] = None,
                    force_reload: bool = False) -> dict[str, type]:
    """Auto-discover Agent subclasses. Returns {name: class}."""
    global _CACHE
    if _CACHE is not None and not force_reload:
        return _CACHE

    if agents_dir is None:
        agents_dir = os.path.dirname(os.path.abspath(__file__))

    parent = os.path.dirname(agents_dir)
    if parent not in sys.path:
        sys.path.insert(0, parent)

    classes: dict[str, type] = {}
    for fn in sorted(os.listdir(agents_dir)):
        if not fn.endswith('.py') or fn in ('__init__.py', 'agent_runtime.py'):
            continue
        try:
            mod = importlib.import_module(f'agents.{fn[:-3]}')
            for _, obj in inspect.getmembers(mod, inspect.isclass):
                if (issubclass(obj, Agent) and obj is not Agent
                        and not inspect.isabstract(obj)):
                    try:
                        classes[obj().name] = obj
                    except Exception:
                        pass
        except Exception as e:
            print(f"[agents] Warning: {fn}: {e}")

    _CACHE = classes
    return classes
