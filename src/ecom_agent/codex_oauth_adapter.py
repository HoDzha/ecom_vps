from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


class CodexOAuthAdapter:
    def __init__(self, model: str = "gpt-5.3-codex", timeout_s: int = 180):
        self.model = model
        self.timeout_s = timeout_s
        self.codex_bin = self._resolve_codex_bin()

    def _resolve_codex_bin(self) -> str:
        explicit = os.getenv("CODEX_CLI_BIN", "").strip()
        if explicit:
            return explicit

        sandbox_bin = Path.home() / ".codex" / ".sandbox-bin" / "codex"
        if sandbox_bin.exists():
            return str(sandbox_bin)

        binary = shutil.which("codex")
        if binary:
            return binary

        raise RuntimeError("codex binary not found. Install Codex CLI or set CODEX_CLI_BIN")

    @staticmethod
    def _strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
        # Minimal strict normalization compatible with Codex output-schema mode.
        result = json.loads(json.dumps(schema))

        def visit(node: Any) -> None:
            if not isinstance(node, dict):
                return
            if node.get("type") == "object":
                props = node.get("properties", {})
                if isinstance(props, dict):
                    node.setdefault("required", list(props.keys()))
                node.setdefault("additionalProperties", False)
            for value in node.values():
                if isinstance(value, dict):
                    visit(value)
                elif isinstance(value, list):
                    for child in value:
                        visit(child)

        visit(result)
        return result

    def _exec(self, prompt_payload: dict[str, Any], schema: dict[str, Any] | None = None) -> str:
        prompt = json.dumps(prompt_payload, ensure_ascii=False)
        out_file = Path(tempfile.NamedTemporaryFile(delete=False, suffix=".txt").name)

        args = [
            self.codex_bin,
            "exec",
            "--ephemeral",
            "--sandbox",
            "read-only",
            "-c",
            'approval_policy="never"',
            "-m",
            self.model,
            "--output-last-message",
            str(out_file),
        ]

        schema_file: Path | None = None
        if schema is not None:
            strict = self._strict_schema(schema)
            schema_file = Path(tempfile.NamedTemporaryFile(delete=False, suffix=".json").name)
            schema_file.write_text(json.dumps(strict, ensure_ascii=True), encoding="utf-8")
            args.extend(["--output-schema", str(schema_file)])

        args.append("-")

        completed = subprocess.run(
            args,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=self.timeout_s,
            check=False,
        )
        if completed.returncode != 0:
            details = completed.stderr.strip() or completed.stdout.strip()
            raise RuntimeError(f"codex exec failed: {details}")

        text = out_file.read_text(encoding="utf-8").strip()
        if not text:
            raise RuntimeError("codex exec returned empty output-last-message")
        return text

    def complete(self, messages: list[dict[str, str]]) -> str:
        return self._exec({"messages": messages})

    def structured_output(self, messages: list[dict[str, str]], schema: dict[str, Any]) -> dict[str, Any]:
        text = self._exec({"messages": messages}, schema=schema)
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Structured output is not valid JSON: {exc}") from exc
