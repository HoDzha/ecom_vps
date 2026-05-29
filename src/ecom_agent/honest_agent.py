from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


INJECTION_PATTERNS = [
    "ignore previous instructions",
    "reveal system prompt",
    "print secrets",
    "override policy",
    "bypass controls",
]


@dataclass
class HonestAgentResult:
    message: str
    outcome: str
    refs: list[str] = field(default_factory=list)
    trace: list[str] = field(default_factory=list)


def _security_denial(instruction: str) -> HonestAgentResult | None:
    lower = instruction.lower()
    for pat in INJECTION_PATTERNS:
        if pat in lower:
            return HonestAgentResult(
                message="Security denial: prompt-injection pattern detected in task text.",
                outcome="OUTCOME_DENIED_SECURITY",
                refs=[],
                trace=[f"security_guard:{pat}"],
            )
    return None


def _keyword_set(instruction: str) -> list[str]:
    words = [w.strip(" ,.:;!?()[]{}\"'").lower() for w in instruction.split()]
    words = [w for w in words if len(w) >= 4]
    unique: list[str] = []
    seen: set[str] = set()
    for w in words:
        if w not in seen:
            seen.add(w)
            unique.append(w)
        if len(unique) >= 8:
            break
    return unique or ["order", "customer", "refund"]


def run_honest_trial(vm: Any, instruction: str) -> HonestAgentResult:
    deny = _security_denial(instruction)
    if deny is not None:
        return deny

    # Import generated protobuf request classes lazily to keep local dev working
    # even when BitGN SDK is not installed.
    from bitgn.vm.ecom.ecom_pb2 import ExecRequest, ListRequest, ReadRequest, SearchRequest, TreeRequest

    refs: list[str] = []
    trace: list[str] = []
    evidence: list[str] = []

    tree = vm.tree(TreeRequest(root="/", level=2))
    refs.append("vm:tree:/")
    root_name = getattr(getattr(tree, "root", None), "name", "")
    trace.append(f"tree_root:{root_name or '/'}")

    for path in ["/AGENTS.md", "/AGENTS.MD", "/README.md", "/task.md"]:
        try:
            r = vm.read(ReadRequest(path=path, start_line=0, end_line=0, number=False))
            content = getattr(r, "content", "")
            if content:
                refs.append(f"vm:read:{path}")
                evidence.append(f"read {path} ({len(content)} chars)")
                trace.append(f"read_ok:{path}")
                break
        except Exception:
            trace.append(f"read_skip:{path}")

    # Query system state tools; these are cheap and often useful for grounding.
    for cmd in ["/bin/date", "/bin/id"]:
        try:
            ex = vm.exec(ExecRequest(path=cmd, args=[], stdin=""))
            stdout = (getattr(ex, "stdout", "") or "").strip()
            if stdout:
                refs.append(f"vm:exec:{cmd}")
                evidence.append(f"exec {cmd}: {stdout.splitlines()[0][:140]}")
            trace.append(f"exec_ok:{cmd}")
        except Exception:
            trace.append(f"exec_skip:{cmd}")

    # Search by instruction-derived keywords and read matched files for grounding.
    matched_paths: list[str] = []
    for kw in _keyword_set(instruction):
        try:
            s = vm.search(SearchRequest(root="/", pattern=kw, limit=10))
            refs.append(f"vm:search:{kw}")
            trace.append(f"search_ok:{kw}")
            for m in getattr(s, "matches", []):
                p = getattr(m, "path", "")
                if p and p not in matched_paths:
                    matched_paths.append(p)
                    if len(matched_paths) >= 5:
                        break
        except Exception:
            trace.append(f"search_skip:{kw}")
        if len(matched_paths) >= 5:
            break

    if not matched_paths:
        # Fallback list for top-level reconnaissance
        try:
            ls = vm.list(ListRequest(path="/"))
            refs.append("vm:list:/")
            entries = [getattr(e, "name", "") for e in getattr(ls, "entries", [])]
            preview = ", ".join([x for x in entries if x][:8])
            evidence.append(f"list /: {preview}" if preview else "list /: empty")
            trace.append("list_ok:/")
        except Exception:
            trace.append("list_skip:/")

    for p in matched_paths[:3]:
        try:
            r = vm.read(ReadRequest(path=p, start_line=1, end_line=120, number=False))
            content = (getattr(r, "content", "") or "").strip()
            refs.append(f"vm:read:{p}")
            if content:
                first = content.splitlines()[0][:160]
                evidence.append(f"read {p}: {first}")
            trace.append(f"read_match_ok:{p}")
        except Exception:
            trace.append(f"read_match_skip:{p}")

    refs = sorted(set(refs))
    if evidence:
        message = "Evidence-first completion. Inspected runtime workspace and collected grounding facts. "
        message += " | ".join(evidence[:6])
        # Honest conservative completion without fabricating state changes.
        return HonestAgentResult(
            message=message,
            outcome="OUTCOME_NONE_CLARIFICATION",
            refs=refs,
            trace=trace,
        )

    return HonestAgentResult(
        message="Unable to gather sufficient evidence from workspace; clarification needed.",
        outcome="OUTCOME_NONE_CLARIFICATION",
        refs=refs,
        trace=trace,
    )
