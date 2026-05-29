from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .models import Outcome, TaskRoute, VerifierReport


class VerifierAgent:
    @staticmethod
    def _validate_outcome_shape(payload: dict[str, Any]) -> list[str]:
        required = {"outcome_type", "status", "result", "citations", "side_effects", "errors"}
        allowed = required
        issues: list[str] = []

        missing = sorted(required - set(payload.keys()))
        extra = sorted(set(payload.keys()) - allowed)
        if missing:
            issues.append(f"missing keys: {', '.join(missing)}")
        if extra:
            issues.append(f"unexpected keys: {', '.join(extra)}")

        if payload.get("outcome_type") != "OUTCOME_ECOM_V1":
            issues.append("outcome_type must be OUTCOME_ECOM_V1")
        if payload.get("status") not in {"success", "needs_clarification", "denied", "failed"}:
            issues.append("invalid status")
        if not isinstance(payload.get("result"), dict):
            issues.append("result must be object")
        if not isinstance(payload.get("citations"), list):
            issues.append("citations must be array")
        if not isinstance(payload.get("side_effects"), list):
            issues.append("side_effects must be array")
        if not isinstance(payload.get("errors"), list):
            issues.append("errors must be array")

        return issues

    def run(self, outcome: Outcome, route: TaskRoute, observed_side_effects: list[dict[str, str]]) -> VerifierReport:
        reason_codes: list[str] = []
        payload: dict[str, Any] = asdict(outcome)
        payload["status"] = outcome.status.value

        schema_issues = self._validate_outcome_shape(payload)
        for issue in schema_issues:
            reason_codes.append(f"SCHEMA_INVALID:{issue}")

        if outcome.outcome_type != route.completion_schema:
            reason_codes.append("PROTOCOL_OUTCOME_TYPE_MISMATCH")

        declared = {(x.type, x.target) for x in outcome.side_effects}
        observed = {(x["type"], x["target"]) for x in observed_side_effects}
        if declared != observed:
            reason_codes.append("SIDE_EFFECTS_MISMATCH")

        if outcome.status.value == "success" and not outcome.result:
            reason_codes.append("SUCCESS_EMPTY_RESULT")

        if route.domain.value == "finance":
            expected_steps = {"s1", "s2", "s3"}
            present_steps = set(outcome.result.keys())
            missing_steps = sorted(expected_steps - present_steps)
            if missing_steps:
                reason_codes.append(f"DOMAIN_FINANCE_MISSING_FACTS:{','.join(missing_steps)}")

            refs = {c.ref for c in outcome.citations}
            if not any(ref.startswith("policy_book:") for ref in refs):
                reason_codes.append("DOMAIN_FINANCE_MISSING_POLICY_CITATION")
            if not any(ref.startswith("customer_records:") for ref in refs):
                reason_codes.append("DOMAIN_FINANCE_MISSING_CUSTOMER_CITATION")
            if not any(ref.startswith("warehouse:") for ref in refs):
                reason_codes.append("DOMAIN_FINANCE_MISSING_WAREHOUSE_CITATION")

            cust = outcome.result.get("s2", {})
            wh = outcome.result.get("s3", {})
            if isinstance(cust, dict) and cust.get("missing") is True and outcome.status.value == "success":
                reason_codes.append("DOMAIN_FINANCE_SUCCESS_WITH_MISSING_CUSTOMER")
            if isinstance(wh, dict) and wh.get("missing") is True and outcome.status.value == "success":
                reason_codes.append("DOMAIN_FINANCE_SUCCESS_WITH_MISSING_WAREHOUSE")

        if route.requires_human_approval and outcome.status.value == "success":
            reason_codes.append("POLICY_HUMAN_APPROVAL_REQUIRED")

        return VerifierReport(passed=not reason_codes, reason_codes=reason_codes)
