TASK_ROUTE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "domain",
        "risk_tier",
        "allowed_tools",
        "completion_schema",
        "requires_human_approval",
    ],
    "properties": {
        "domain": {"type": "string", "enum": ["inbox", "filesystem", "ops", "finance", "security", "other"]},
        "risk_tier": {"type": "string", "enum": ["low", "medium", "high"]},
        "allowed_tools": {"type": "array", "items": {"type": "string"}},
        "completion_schema": {"type": "string"},
        "requires_human_approval": {"type": "boolean"},
    },
}

EXECUTION_PLAN_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["steps"],
    "properties": {
        "steps": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["step_id", "description", "tool", "args"],
                "properties": {
                    "step_id": {"type": "string"},
                    "description": {"type": "string"},
                    "tool": {"type": "string"},
                    "args": {"type": "object"},
                },
            },
        }
    },
}

OUTCOME_ECOM_V1_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["outcome_type", "status", "result", "citations", "side_effects", "errors"],
    "properties": {
        "outcome_type": {"type": "string", "const": "OUTCOME_ECOM_V1"},
        "status": {"type": "string", "enum": ["success", "needs_clarification", "denied", "failed"]},
        "result": {"type": "object"},
        "citations": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["source", "ref"],
                "properties": {"source": {"type": "string"}, "ref": {"type": "string"}},
            },
        },
        "side_effects": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["type", "target"],
                "properties": {"type": {"type": "string"}, "target": {"type": "string"}},
            },
        },
        "errors": {"type": "array", "items": {"type": "string"}},
    },
}

VERIFIER_REPORT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["passed", "reason_codes"],
    "properties": {
        "passed": {"type": "boolean"},
        "reason_codes": {"type": "array", "items": {"type": "string"}},
    },
}
