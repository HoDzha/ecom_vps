from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class ModelProfile:
    provider: str
    adapter: str
    auth: str
    solver_model: str
    verifier_model: str


def load_model_profile() -> ModelProfile:
    provider = os.getenv("ECOM_PROVIDER", "local").strip().lower()
    if provider == "openai":
        model = os.getenv("ECOM_SOLVER_MODEL", "gpt-5.3-codex")
        verifier_model = os.getenv("ECOM_VERIFIER_MODEL", model)
        return ModelProfile(
            provider="openai",
            adapter="codex_oauth",
            auth="chatgpt_oauth",
            solver_model=model,
            verifier_model=verifier_model,
        )

    return ModelProfile(
        provider="local",
        adapter="local_mock",
        auth="none",
        solver_model="local-solver",
        verifier_model="local-verifier",
    )
