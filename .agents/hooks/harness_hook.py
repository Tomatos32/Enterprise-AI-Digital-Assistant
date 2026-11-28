#!/usr/bin/env python3
"""Antigravity lifecycle hook handler for Enterprise AI Digital Assistant Harness.

Implements:
- `session-start`: injects a compact Token Budget & Workflow reminder once per session.
- `pre-read`: enforces read-deny on `docs/sample_kb/**`, `docs/archive/**`, and sealed
  historical `.harness/runs/**` folders while permitting active in-progress runs.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
ALWAYS_DENY_PREFIXES = ("docs/sample_kb/", "docs/archive/")
ISSUE_ID_RE = re.compile(r"\b(?:Issue|Ops|Sprint-F)-\d{2,4}\b", re.IGNORECASE)


def read_payload() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def normalize_rel_path(raw_path: str) -> str:
    cleaned = raw_path.strip().strip("\"'").replace("\\", "/")
    root_posix = REPO_ROOT.as_posix().rstrip("/")
    if cleaned.lower().startswith(root_posix.lower() + "/"):
        return cleaned[len(root_posix) + 1 :]
    if cleaned.startswith("./"):
        return cleaned[2:]
    return cleaned


def extract_target_path(tool_args: dict[str, Any]) -> str:
    for key in ("Path", "AbsolutePath", "path", "file_path", "TargetFile"):
        val = tool_args.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return ""


def handle_session_start() -> dict[str, Any]:
    return {
        "injectSteps": [
            {
                "systemMessage": {
                    "systemMessage": (
                        "[Token Budget] Keep shell stdout <=50 lines: wrap noisy checks with "
                        "`PYTHONUTF8=1 backend/.venv/Scripts/python.exe scripts/harness_run.py --name <gate> -- <cmd>`; "
                        "pytest use `-q --tb=short --no-header`; long logs pipe through "
                        "`Select-String`/`Select-Object -Last 50` (PowerShell) or `grep`/`tail -n 50` (Bash). "
                        "Pre-generate Wave 4 scope/diff via `scripts/harness_prepare_review.py <ID>` and close out via `scripts/harness_seal.py <ID>`."
                    )
                }
            }
        ]
    }


def handle_pre_read(payload: dict[str, Any]) -> dict[str, Any]:
    tool_call = payload.get("toolCall") or {}
    args = tool_call.get("args") or {}
    raw_path = extract_target_path(args if isinstance(args, dict) else {})
    if not raw_path:
        return {"decision": "allow"}

    rel_path = normalize_rel_path(raw_path)
    rel_lower = rel_path.lower()

    for prefix in ALWAYS_DENY_PREFIXES:
        if prefix in rel_lower:
            return {
                "decision": "deny",
                "reason": f"[Read Guard] Blocked reading `{rel_path}` ({prefix}** is excluded from normal agent reads to prevent context bloat).",
            }

    marker = ".harness/runs/"
    if marker in rel_lower:
        after = rel_path[rel_lower.index(marker) + len(marker) :]
        run_id = after.split("/", 1)[0]
        if run_id:
            last_input = str(payload.get("lastUserInput") or "")
            explicitly_named = any(m.group(0).lower() == run_id.lower() for m in ISSUE_ID_RE.finditer(last_input))
            sealed = (REPO_ROOT / ".harness" / "runs" / run_id / "summary.json").is_file()
            if sealed and not explicitly_named:
                return {
                    "decision": "deny",
                    "reason": (
                        f"[Read Guard] Blocked reading sealed historical run `.harness/runs/{run_id}/`. "
                        "Read only the active run or Summary.md unless the user explicitly references that ID."
                    ),
                }

    return {"decision": "allow"}


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    mode = args[0] if args else "pre-read"
    payload = read_payload()
    if mode == "session-start":
        result = handle_session_start()
    elif mode == "pre-read":
        result = handle_pre_read(payload)
    else:
        result = {}
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
