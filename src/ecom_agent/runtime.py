from __future__ import annotations

from dataclasses import asdict

from .agents import PlannerAgent, RouterAgent, SolverAgent
from .data_sources import CUSTOMER_RECORDS, POLICY_BOOK, WAREHOUSE
from .models import Outcome, OutcomeStatus
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


def run_task(user_task: str, customer_id: str = "cust_001", order_id: str = "ord_1001") -> dict:
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
    report = verifier.run(candidate, route, ledger.events)
    if report.passed:
        return {
            "submit": True,
            "route": asdict(route),
            "plan": asdict(plan),
            "outcome": asdict(candidate),
            "verifier": asdict(report),
        }

    # repair_once placeholder: preserve original solver facts and verifier reasons
    # so failure clusters stay actionable for evolution loop.
    candidate2 = Outcome(
        outcome_type=candidate.outcome_type,
        status=OutcomeStatus.FAILED,
        result=candidate.result,
        citations=candidate.citations,
        side_effects=candidate.side_effects,
        errors=report.reason_codes,
    )

    return {
        "submit": False,
        "route": asdict(route),
        "plan": asdict(plan),
        "outcome": asdict(candidate2),
        "verifier": asdict(report),
    }
