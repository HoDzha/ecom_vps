# Contributing

## Setup

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

## Run

```bash
PYTHONPATH=src python3 -m ecom_agent.cli "Customer requests refund for late package"
PYTHONPATH=src python3 -m ecom_agent.eval
```

## Pull requests

- Keep changes scoped and atomic.
- Add/adjust eval cases when behavior changes.
- Do not commit secrets, `.env`, or local auth artifacts.
