from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .codex_oauth_adapter import CodexOAuthAdapter
from .config import ModelProfile, load_model_profile


class LocalMockAdapter:
    def __init__(self, model: str = "local-solver"):
        self.model = model

    def complete(self, messages: list[dict[str, str]]) -> str:
        _ = messages
        return "LOCAL_MOCK_OK"

    def structured_output(self, messages: list[dict[str, str]], schema: dict[str, Any]) -> dict[str, Any]:
        _ = messages
        # Minimal object that conforms to common "answer" schemas.
        props = schema.get("properties", {}) if isinstance(schema, dict) else {}
        out: dict[str, Any] = {}
        for key, meta in props.items():
            meta_type = meta.get("type") if isinstance(meta, dict) else None
            if meta_type == "string":
                out[key] = "LOCAL_MOCK_OK"
            elif meta_type == "boolean":
                out[key] = True
            elif meta_type == "array":
                out[key] = []
            elif meta_type == "object":
                out[key] = {}
            else:
                out[key] = None
        return out


class ModelRouter:
    def __init__(self, profile: ModelProfile | None = None):
        self.profile = profile or load_model_profile()

    def get_solver(self):
        if self.profile.provider == "openai" and self.profile.adapter == "codex_oauth":
            return CodexOAuthAdapter(model=self.profile.solver_model)
        return LocalMockAdapter(model=self.profile.solver_model)

    def describe(self) -> dict[str, Any]:
        return asdict(self.profile)
