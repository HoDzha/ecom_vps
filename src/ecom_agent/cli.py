from __future__ import annotations

import json
import sys

from .bitgn_runner import run_bitgn
from .env_loader import load_dotenv
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
    load_dotenv()
    args = [x for x in sys.argv[1:] if x.strip()]
    use_llm = False
    use_bitgn = False
    if "--llm" in args:
        use_llm = True
        args.remove("--llm")
    if "--bitgn" in args:
        use_bitgn = True
        args.remove("--bitgn")

    if use_bitgn:
        # Remaining args are treated as optional task_id filter, e.g. t01 t04.
        try:
            result = run_bitgn(task_filter=args or None)
        except Exception as exc:
            print(json.dumps({"error": str(exc)}, ensure_ascii=True, indent=2))
            return 1
        print(json.dumps(result, ensure_ascii=True, indent=2, default=str))
        return 0

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
