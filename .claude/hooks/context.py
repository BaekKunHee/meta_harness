#!/usr/bin/env python3
"""Inject the harness's bounded context into Claude Code sessions and subagents."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


SUPPORTED_EVENTS = {"SessionStart", "SubagentStart"}


def _read_payload() -> dict[str, Any]:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError) as error:
        raise ValueError("hook input must be one JSON object") from error
    if not isinstance(payload, dict):
        raise ValueError("hook input must be one JSON object")
    return payload


def _project_root() -> Path:
    configured = os.environ.get("CLAUDE_PROJECT_DIR")
    return (
        Path(configured).resolve()
        if configured
        else Path(__file__).resolve().parents[2]
    )


def _load_context(root: Path) -> str:
    harness = root / ".harness/harness.py"
    if not harness.is_file():
        raise RuntimeError("repository harness entrypoint is missing")
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-S",
            "-B",
            str(harness),
            "--root",
            str(root),
            "context",
            "--summary",
        ],
        cwd=root,
        text=True,
        capture_output=True,
        timeout=8,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(detail or "repository context command failed")
    return result.stdout


def main() -> int:
    try:
        payload = _read_payload()
        event_name = payload.get("hook_event_name")
        if event_name not in SUPPORTED_EVENTS:
            raise ValueError(f"unsupported hook event: {event_name!r}")
        context = _load_context(_project_root())
    except (OSError, RuntimeError, subprocess.SubprocessError, ValueError) as error:
        print(f"Claude context hook failed: {error}", file=sys.stderr)
        return 1

    if event_name == "SubagentStart":
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "SubagentStart",
                        "additionalContext": context,
                    }
                },
                ensure_ascii=False,
            )
        )
    else:
        print(context, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
