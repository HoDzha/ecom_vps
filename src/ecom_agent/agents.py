from __future__ import annotations

from dataclasses import asdict

from .models import Citation, Domain, ExecutionPlan, Outcome, OutcomeStatus, PlanStep, RiskTier, SideEffect, TaskRoute
from .tool_rails import ToolRails


class RouterAgent:
    def run(self, user_task: str) -> TaskRoute:
        lower = user_task.lower()
        fraud_like = any(word in lower for word in ["fraud", "chargeback", "stolen card"])
        if any(word in lower for word in ["refund", "return", "payment", "chargeback", "fraud"]):
            return TaskRoute(
                domain=Domain.FINANCE,
                risk_tier=RiskTier.HIGH if fraud_like else RiskTier.MEDIUM,
                allowed_tools=["search_policy", "read_customer", "read_warehouse", "submit"],
                completion_schema="OUTCOME_ECOM_V1",
                requires_human_approval=fraud_like,
            )
        return TaskRoute(
            domain=Domain.OTHER,
            risk_tier=RiskTier.LOW,
            allowed_tools=["search_policy", "submit"],
            completion_schema="OUTCOME_ECOM_V1",
            requires_human_approval=False,
        )


class PlannerAgent:
    def run(self, route: TaskRoute, user_task: str, customer_id: str = "cust_001", order_id: str = "ord_1001") -> ExecutionPlan:
        steps = [
            PlanStep(step_id="s1", description="Read relevant policy", tool="search_policy", args={"query": user_task}),
        ]
        if route.domain == Domain.FINANCE:
            steps.extend(
                [
                    PlanStep(
                        step_id="s2",
                        description="Read customer profile for eligibility",
                        tool="read_customer",
                        args={"customer_id": customer_id},
                    ),
                    PlanStep(
                        step_id="s3",
                        description="Read warehouse delivery facts",
                        tool="read_warehouse",
                        args={"order_id": order_id},
                    ),
                ]
            )
        return ExecutionPlan(steps=steps)


class SolverAgent:
    def run(self, plan: ExecutionPlan, rails: ToolRails) -> Outcome:
        result: dict[str, object] = {}
        citations: list[Citation] = []

        for step in plan.steps:
            output = rails.call(step.tool, step.args)
            result[step.step_id] = output.get("data", {})
            citations.append(Citation(source=f"tool:{step.tool}", ref=output.get("ref", "unknown")))

        return Outcome(
            outcome_type="OUTCOME_ECOM_V1",
            status=OutcomeStatus.SUCCESS,
            result=result,
            citations=citations,
            side_effects=[SideEffect(type=e["type"], target=e["target"]) for e in rails.ledger.events],
            errors=[],
        )


def to_dict_dataclass(obj):
    return asdict(obj)
