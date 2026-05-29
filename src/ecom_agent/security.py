from __future__ import annotations

from typing import Any

INJECTION_PATTERNS = [
    "ignore previous instructions",
    "reveal system prompt",
    "print secrets",
    "override policy",
    "bypass controls",
]

SENSITIVE_KEYS = {
    "email",
    "phone",
    "address",
    "card_number",
    "cvv",
    "token",
    "secret",
    "password",
}


def detect_prompt_injection(text: str) -> bool:
    lower = text.lower()
    return any(p in lower for p in INJECTION_PATTERNS)


def redact_sensitive(obj: Any) -> Any:
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            if k.lower() in SENSITIVE_KEYS:
                out[k] = "[REDACTED]"
            else:
                out[k] = redact_sensitive(v)
        return out
    if isinstance(obj, list):
        return [redact_sensitive(x) for x in obj]
    return obj
