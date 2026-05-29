from __future__ import annotations

import json
import os
from typing import Any

from .honest_agent import run_honest_trial


def _load_bitgn_sdk():
    try:
        from bitgn.harness_connect import HarnessServiceClientSync
        from bitgn.harness_pb2 import (
            EndTrialRequest,
            GetBenchmarkRequest,
            StartRunRequest,
            StartTrialRequest,
            StatusRequest,
            SubmitRunRequest,
        )
        from bitgn.vm.ecom.ecom_connect import EcomRuntimeClientSync
        from bitgn.vm.ecom.ecom_pb2 import AnswerRequest, Outcome
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "BitGN SDK is not installed. Install official packages from buf.build/gen/python "
            "(see README section 'BitGN integration')."
        ) from exc

    return {
        "HarnessServiceClientSync": HarnessServiceClientSync,
        "AnswerRequest": AnswerRequest,
        "EndTrialRequest": EndTrialRequest,
        "GetBenchmarkRequest": GetBenchmarkRequest,
        "StartRunRequest": StartRunRequest,
        "StartTrialRequest": StartTrialRequest,
        "StatusRequest": StatusRequest,
        "SubmitRunRequest": SubmitRunRequest,
        "EcomRuntimeClientSync": EcomRuntimeClientSync,
        "Outcome": Outcome,
    }


def _map_outcome(outcome: dict[str, Any], outcome_enum: Any) -> int:
    status = outcome.get("status")
    errors = set(outcome.get("errors", []))
    if status == "success":
        return outcome_enum.OUTCOME_OK
    if status == "needs_clarification":
        return outcome_enum.OUTCOME_NONE_CLARIFICATION
    if status == "denied":
        return outcome_enum.OUTCOME_DENIED_SECURITY
    if "SECURITY_PROMPT_INJECTION_DETECTED" in errors:
        return outcome_enum.OUTCOME_DENIED_SECURITY
    return outcome_enum.OUTCOME_ERR_INTERNAL


def _map_honest_outcome(outcome_name: str, outcome_enum: Any) -> int:
    mapping = {
        "OUTCOME_OK": outcome_enum.OUTCOME_OK,
        "OUTCOME_DENIED_SECURITY": outcome_enum.OUTCOME_DENIED_SECURITY,
        "OUTCOME_NONE_CLARIFICATION": outcome_enum.OUTCOME_NONE_CLARIFICATION,
        "OUTCOME_NONE_UNSUPPORTED": outcome_enum.OUTCOME_NONE_UNSUPPORTED,
        "OUTCOME_ERR_INTERNAL": outcome_enum.OUTCOME_ERR_INTERNAL,
    }
    return mapping.get(outcome_name, outcome_enum.OUTCOME_ERR_INTERNAL)


def _mode_for_bench(bench_id: str) -> str:
    lower = bench_id.lower()
    if "prod" in lower or "competition" in lower:
        return "competition"
    return "practice"


def run_bitgn(task_filter: list[str] | None = None) -> dict[str, Any]:
    sdk = _load_bitgn_sdk()
    HarnessServiceClientSync = sdk["HarnessServiceClientSync"]
    AnswerRequest = sdk["AnswerRequest"]
    EndTrialRequest = sdk["EndTrialRequest"]
    GetBenchmarkRequest = sdk["GetBenchmarkRequest"]
    StartRunRequest = sdk["StartRunRequest"]
    StartTrialRequest = sdk["StartTrialRequest"]
    StatusRequest = sdk["StatusRequest"]
    SubmitRunRequest = sdk["SubmitRunRequest"]
    EcomRuntimeClientSync = sdk["EcomRuntimeClientSync"]
    Outcome = sdk["Outcome"]

    host = os.getenv("BITGN_HOST", "https://api.bitgn.com")
    api_key = os.getenv("BITGN_API_KEY", "").strip()
    bench_id = os.getenv("BENCH_ID") or os.getenv("BENCHMARK_ID") or "bitgn/ecom1-dev"
    run_name = os.getenv("BITGN_RUN_NAME", "ECOM Agent Scaffold")

    if not api_key:
        raise RuntimeError("BITGN_API_KEY is required")

    client = HarnessServiceClientSync(host)
    _ = client.status(StatusRequest())
    bench = client.get_benchmark(GetBenchmarkRequest(benchmark_id=bench_id))

    run = client.start_run(
        StartRunRequest(
            name=run_name,
            benchmark_id=bench_id,
            api_key=api_key,
        )
    )

    results: list[dict[str, Any]] = []
    mode = _mode_for_bench(bench_id)

    for trial_id in run.trial_ids:
        trial = client.start_trial(StartTrialRequest(trial_id=trial_id))
        if task_filter and trial.task_id not in task_filter:
            client.end_trial(EndTrialRequest(trial_id=trial.trial_id))
            continue

        vm = EcomRuntimeClientSync(trial.harness_url)
        honest = run_honest_trial(vm, trial.instruction)
        vm.answer(
            AnswerRequest(
                message=honest.message,
                outcome=_map_honest_outcome(honest.outcome, Outcome),
                refs=honest.refs,
            )
        )

        client.end_trial(EndTrialRequest(trial_id=trial.trial_id))
        results.append({
            "task_id": trial.task_id,
            "trial_id": trial.trial_id,
            "agent_outcome": honest.outcome,
            "refs_count": len(honest.refs),
            "trace": honest.trace[:8],
        })

    submit = client.submit_run(SubmitRunRequest(run_id=run.run_id, force=True))
    return {
        "host": host,
        "benchmark_id": bench.benchmark_id,
        "run_id": run.run_id,
        "score_available": bool(submit.score_available),
        "score": float(submit.score) if submit.score_available else None,
        "trials": results,
    }
