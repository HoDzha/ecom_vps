from __future__ import annotations

import os
from pathlib import Path


def load_dotenv(path: str = ".env") -> None:
    file = Path(path)
    if not file.exists():
        return

    for line in file.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        k = key.strip()
        v = value.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v
