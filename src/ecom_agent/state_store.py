from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TrialStateStore:
    task_context: dict[str, Any] = field(default_factory=dict)
    working_memory: dict[str, Any] = field(default_factory=dict)
    tool_history: list[dict[str, Any]] = field(default_factory=list)
    side_effects: list[dict[str, str]] = field(default_factory=list)
    policy_state: dict[str, Any] = field(default_factory=dict)

    def record_tool_call(self, tool: str, args: dict[str, Any], output: dict[str, Any]) -> None:
        self.tool_history.append({
            "tool": tool,
            "args": args,
            "ref": output.get("ref", "unknown"),
            "trust": output.get("trust", "derived"),
        })

    def snapshot(self) -> dict[str, Any]:
        return {
            "task_context": self.task_context,
            "working_memory": self.working_memory,
            "tool_history": self.tool_history,
            "side_effects": self.side_effects,
            "policy_state": self.policy_state,
        }
