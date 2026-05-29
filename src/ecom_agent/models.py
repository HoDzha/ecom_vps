from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Domain(str, Enum):
    INBOX = "inbox"
    FILESYSTEM = "filesystem"
    OPS = "ops"
    FINANCE = "finance"
    SECURITY = "security"
    OTHER = "other"


class RiskTier(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class OutcomeStatus(str, Enum):
    SUCCESS = "success"
    NEEDS_CLARIFICATION = "needs_clarification"
    DENIED = "denied"
    FAILED = "failed"


@dataclass
class TaskRoute:
    domain: Domain
    risk_tier: RiskTier
    allowed_tools: list[str]
    completion_schema: str
    requires_human_approval: bool


@dataclass
class PlanStep:
    step_id: str
    description: str
    tool: str
    args: dict[str, Any]


@dataclass
class ExecutionPlan:
    steps: list[PlanStep]


@dataclass
class Citation:
    source: str
    ref: str


@dataclass
class SideEffect:
    type: str
    target: str


@dataclass
class Outcome:
    outcome_type: str
    status: OutcomeStatus
    result: dict[str, Any]
    citations: list[Citation] = field(default_factory=list)
    side_effects: list[SideEffect] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class VerifierReport:
    passed: bool
    reason_codes: list[str] = field(default_factory=list)
