# ECOM Agent Scaffold

Minimal Codex-on-Rails scaffold for BitGN E-commerce challenge.

## Includes

- Fixed role contracts: `RouterAgent`, `PlannerAgent`, `SolverAgent`, `VerifierAgent`
- Tool rails: allowlist, args type check, trust tags, side-effect ledger, bounded retries
- Typed outcome and strict verifier gate before submit
- Model routing with OpenAI Codex OAuth adapter (`codex exec`) or local mock adapter

## Run baseline runtime

```bash
PYTHONPATH=src python3 -m ecom_agent.cli "Customer requests refund for late package"
```

Optional IDs for data-backed tools:

```bash
PYTHONPATH=src python3 -m ecom_agent.cli "Refund requested"  # defaults: cust_001 / ord_1001
```

## Run with model router (`--llm`)

```bash
PYTHONPATH=src python3 -m ecom_agent.cli --llm "Customer requests refund for late package"
```

Default provider is local mock.

## Enable OpenAI Codex OAuth profile

1. Install Codex CLI and login once:

```bash
npm i -g @openai/codex
codex login
codex login status
```

2. Set provider env vars:

```bash
export ECOM_PROVIDER=openai
export ECOM_SOLVER_MODEL=gpt-5.3-codex
# Optional if codex is not on PATH
# export CODEX_CLI_BIN=/absolute/path/to/codex
```

3. Run with `--llm`:

```bash
PYTHONPATH=src python3 -m ecom_agent.cli --llm "Customer requests refund for late package"
```

This path uses `codex exec --ephemeral --sandbox read-only` and relies on Codex CLI OAuth cache.

## Eval harness

Run batch scenarios and get pass-rate plus failure clusters:

```bash
PYTHONPATH=src python3 -m ecom_agent.eval
```

## Runtime contract (v1)

`run_task` uses normalized task input:

- `task` (string)
- `customer_id` (string)
- `order_id` (string)
- `mode` (`practice|competition`)

Result contains:

- `submit` gate
- `route`, `plan`, `outcome`, `verifier`
- `state` snapshot with `task_context`, `working_memory`, `tool_history`, `side_effects`, `policy_state`

Security rails:

- prompt-injection detection returns `denied` with `SECURITY_PROMPT_INJECTION_DETECTED`
- sensitive fields in output are redacted

Repair behavior:

- missing customer/order records -> `needs_clarification` with `missing_fields`
- high-risk manual-review routes -> `denied` with policy reason

## Publish to GitHub

```bash
git init
git add .
git commit -m "Initial commit: ecom agent scaffold"
git branch -M main
git remote add origin <your_repo_url>
git push -u origin main
```

## BitGN integration

This project includes a BitGN run lifecycle runner (`--bitgn`) that uses:

- `HarnessServiceClientSync` for benchmark/run/trial lifecycle
- `EcomRuntimeClientSync` for trial answer submission
- real workspace inspection per trial (`tree/read/search/list/exec`) before `answer`

Environment variables (loaded from `.env` automatically):

- `BITGN_API_KEY` (required)
- `BITGN_HOST` (optional, default: `https://api.bitgn.com`)
- `BENCH_ID` or `BENCHMARK_ID` (optional, default: `bitgn/ecom1-dev`)
- `BITGN_RUN_NAME` (optional)

Install official BitGN SDK packages (from `buf.build/gen/python`) before running:

```bash
python -m pip install --extra-index-url https://buf.build/gen/python \\
  bitgn-api-connectrpc-python \\
  bitgn-api-protocolbuffers-python
```

Run full benchmark:

```bash
PYTHONPATH=src python3 -m ecom_agent.cli --bitgn
```

Run selected tasks only:

```bash
PYTHONPATH=src python3 -m ecom_agent.cli --bitgn t01 t04
```
