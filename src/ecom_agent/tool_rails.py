from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ToolCallRecord:
    tool: str
    args: dict[str, Any]
    output: dict[str, Any]
    trust: str


@dataclass
class SideEffectLedger:
    events: list[dict[str, str]] = field(default_factory=list)

    def append(self, effect_type: str, target: str) -> None:
        self.events.append({"type": effect_type, "target": target})


class ToolRails:
    def __init__(self, allowed_tools: list[str], ledger: SideEffectLedger, tools: dict[str, Callable[..., dict[str, Any]]]):
        self.allowed_tools = set(allowed_tools)
        self.ledger = ledger
        self.tools = tools
        self.history: list[ToolCallRecord] = []

    def call(self, tool: str, args: dict[str, Any], max_retries: int = 2) -> dict[str, Any]:
        if tool not in self.allowed_tools:
            raise PermissionError(f"Tool '{tool}' is not allowed by route")
        if tool not in self.tools:
            raise ValueError(f"Tool '{tool}' is not registered")
        if not isinstance(args, dict):
            raise TypeError("Tool args must be a JSON object")

        last_error: Exception | None = None
        for _ in range(max_retries + 1):
            try:
                output = self.tools[tool](**args)
                trust = output.get("trust", "derived")
                side_effect = output.get("side_effect")
                if isinstance(side_effect, dict):
                    self.ledger.append(side_effect.get("type", "unknown"), side_effect.get("target", "unknown"))
                self.history.append(ToolCallRecord(tool=tool, args=args, output=output, trust=trust))
                return output
            except Exception as exc:  # deterministic bounded retries
                last_error = exc
        raise RuntimeError(f"Tool call failed after retries: {last_error}")
