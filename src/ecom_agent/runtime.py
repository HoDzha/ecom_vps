from __future__ import annotations

from dataclasses import asdict

from .agents import PlannerAgent, RouterAgent, SolverAgent
from .data_sources import CUSTOMER_RECORDS, POLICY_BOOK, WAREHOUSE
from .models import Outcome, OutcomeStatus
from .security import detect_prompt_injection, redact_sensitive
from .state_store import TrialStateStore
from .tool_rails import SideEffectLedger, ToolRails
from .verifier import VerifierAgent


def _tool_search_policy(query: str) -> dict:
    tokens = set(query.lower().split())
    best = None
    best_score = -1
    for entry in POLICY_BOOK:
        score = sum(1 for tag in entry["tags"] if tag in tokens)
        if score > best_score:
            best = entry
            best_score = score

    if best is None:
        best = POLICY_BOOK[0]

    return {
        "data": {
            "policy_id": best["id"],
            "title": best["title"],
            "excerpt": best["text"],
            "query": query,
        },
        "ref": f"policy_book:{best['id']}",
        "trust": "trusted",
    }


def _tool_read_customer(customer_id: str) -> dict:
    data = CUSTOMER_RECORDS.get(customer_id)
    if data is None:
        return {
            "data": {"customer_id": customer_id, "missing": True},
            "ref": f"customer_records:{customer_id}",
            "trust": "trusted",
        }
    return {
        "data": data,
        "ref": f"customer_records:{customer_id}",
        "trust": "trusted",
    }


def _tool_read_warehouse(order_id: str) -> dict:
    data = WAREHOUSE.get(order_id)
    if data is None:
        return {
            "data": {"order_id": order_id, "missing": True},
            "ref": f"warehouse:{order_id}",
            "trust": "trusted",
        }
    return {
        "data": data,
        "ref": f"warehouse:{order_id}",
        "trust": "trusted",
    }


def _validate_task_input(task: dict) -> list[str]:
    required = {"task", "customer_id", "order_id", "mode"}
    issues: list[str] = []
    missing = sorted(required - set(task.keys()))
    if missing:
        issues.append(f"TASK_INPUT_MISSING:{','.join(missing)}")
    if task.get("mode") not in {"practice", "competition"}:
        issues.append("TASK_INPUT_INVALID_MODE")
    for key in ["task", "customer_id", "order_id"]:
        value = task.get(key)
        if not isinstance(value, str) or not value.strip():
            issues.append(f"TASK_INPUT_INVALID_{key.upper()}")
    return issues


def _repair_once(candidate: Outcome, reason_codes: list[str]) -> Outcome:
    missing_fields: list[str] = []
    if "DOMAIN_FINANCE_SUCCESS_WITH_MISSING_CUSTOMER" in reason_codes:
        missing_fields.append("customer_id")
    if "DOMAIN_FINANCE_SUCCESS_WITH_MISSING_WAREHOUSE" in reason_codes:
        missing_fields.append("order_id")
    if missing_fields:
        return Outcome(
            outcome_type=candidate.outcome_type,
            status=OutcomeStatus.NEEDS_CLARIFICATION,
            result={
                "missing_fields": missing_fields,
                "message": "Required records are missing for a safe decision.",
            },
            citations=candidate.citations,
            side_effects=candidate.side_effects,
            errors=reason_codes,
        )

    if "POLICY_HUMAN_APPROVAL_REQUIRED" in reason_codes:
        return Outcome(
            outcome_type=candidate.outcome_type,
            status=OutcomeStatus.DENIED,
            result={"message": "Manual review required by policy."},
            citations=candidate.citations,
            side_effects=candidate.side_effects,
            errors=reason_codes,
        )

    return Outcome(
        outcome_type=candidate.outcome_type,
        status=OutcomeStatus.FAILED,
        result=candidate.result,
        citations=candidate.citations,
        side_effects=candidate.side_effects,
        errors=reason_codes,
    )


def run_task(user_task: str, customer_id: str = "cust_001", order_id: str = "ord_1001", mode: str = "practice") -> dict:
    task_input = {
        "task": user_task,
        "customer_id": customer_id,
        "order_id": order_id,
        "mode": mode,
    }
    input_issues = _validate_task_input(task_input)
    if input_issues:
        return {
            "submit": False,
            "task_input": task_input,
            "route": None,
            "plan": None,
            "outcome": {
                "outcome_type": "OUTCOME_ECOM_V1",
                "status": "failed",
                "result": {},
                "citations": [],
                "side_effects": [],
                "errors": input_issues,
            },
            "verifier": {"passed": False, "reason_codes": input_issues},
            "state": {},
        }

    state = TrialStateStore(
        task_context=task_input,
        policy_state={"blind_window": mode == "competition", "human_in_the_loop_allowed": False},
    )

    if detect_prompt_injection(user_task):
        reason_codes = ["SECURITY_PROMPT_INJECTION_DETECTED"]
        return {
            "submit": False,
            "task_input": task_input,
            "route": None,
            "plan": None,
            "outcome": {
                "outcome_type": "OUTCOME_ECOM_V1",
                "status": "denied",
                "result": {"message": "Request denied by security policy."},
                "citations": [],
                "side_effects": [],
                "errors": reason_codes,
            },
            "verifier": {"passed": False, "reason_codes": reason_codes},
            "state": state.snapshot(),
        }

    router = RouterAgent()
    planner = PlannerAgent()
    solver = SolverAgent()
    verifier = VerifierAgent()

    route = router.run(user_task)
    plan = planner.run(route, user_task, customer_id=customer_id, order_id=order_id)

    ledger = SideEffectLedger()
    tools = {
        "search_policy": _tool_search_policy,
        "read_customer": _tool_read_customer,
        "read_warehouse": _tool_read_warehouse,
        "submit": lambda **_: {"data": {"ok": True}, "ref": "tool:submit", "trust": "derived"},
    }
    rails = ToolRails(route.allowed_tools, ledger, tools)

    candidate = solver.run(plan, rails)
    state.working_memory = {"route_domain": route.domain.value, "plan_steps": [s.step_id for s in plan.steps]}
    for rec in rails.history:
        state.record_tool_call(rec.tool, rec.args, rec.output)
    state.side_effects = ledger.events

    report = verifier.run(candidate, route, ledger.events)
    if report.passed:
        return {
            "submit": True,
            "task_input": task_input,
            "route": asdict(route),
            "plan": asdict(plan),
            "outcome": redact_sensitive(asdict(candidate)),
            "verifier": asdict(report),
            "state": state.snapshot(),
        }

    candidate2 = _repair_once(candidate, report.reason_codes)
    report2 = verifier.run(candidate2, route, ledger.events)

    return {
        "submit": report2.passed,
        "task_input": task_input,
        "route": asdict(route),
        "plan": asdict(plan),
        "outcome": redact_sensitive(asdict(candidate2)),
        "verifier": asdict(report2),
        "state": state.snapshot(),
    }
