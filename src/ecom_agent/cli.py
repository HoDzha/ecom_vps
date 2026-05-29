from __future__ import annotations

import json
import sys

from .model_router import ModelRouter
from .runtime import run_task


LLM_SCHEMA_V1 = {
    "type": "object",
    "properties": {
        "decision": {"type": "string"},
        "reason": {"type": "string"},
        "needs_human_approval": {"type": "boolean"},
    },
    "required": ["decision", "reason", "needs_human_approval"],
    "additionalProperties": False,
}


def main() -> int:
    args = [x for x in sys.argv[1:] if x.strip()]
    use_llm = False
    if "--llm" in args:
        use_llm = True
        args.remove("--llm")

    task = " ".join(args).strip() or "Customer asks refund after delayed delivery"
    result = run_task(task)
    if use_llm:
        router = ModelRouter()
        solver = router.get_solver()
        llm_output = solver.structured_output(
            messages=[
                {"role": "system", "content": "You are an e-commerce policy assistant. Reply with strict JSON only."},
                {"role": "user", "content": task},
            ],
            schema=LLM_SCHEMA_V1,
        )
        result["llm"] = {
            "profile": router.describe(),
            "output": llm_output,
        }
    print(json.dumps(result, ensure_ascii=True, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
