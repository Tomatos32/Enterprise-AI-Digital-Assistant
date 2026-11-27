"""Hard-capped command runner for Harness Engineering.

Runs a shell/CLI command, writes full stdout+stderr to `.harness/logs/<ts>_<name>.log`,
and prints at most `--max-lines` (default 50) tail lines to stdout while preserving
the exact exit code of the wrapped command.

Usage:
    backend/.venv/Scripts/python.exe scripts/harness_run.py --name pytest -- backend/.venv/Scripts/python.exe -m pytest backend/tests/ -q --tb=line --no-header
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = REPO_ROOT / ".harness" / "logs"


def sanitize_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name.strip())
    return cleaned or "cmd"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run a command with full log archival and hard-capped stdout.",
    )
    parser.add_argument("--name", default="cmd", help="Short label for the log filename.")
    parser.add_argument(
        "--max-lines",
        type=int,
        default=50,
        help="Maximum output lines printed to stdout (default: 50).",
    )
    parser.add_argument(
        "--cwd",
        default=str(REPO_ROOT),
        help="Working directory for the command (default: repo root).",
    )
    parser.add_argument(
        "--filter",
        dest="filter_regex",
        default="",
        help="Optional regex to keep only matching lines before tail truncation.",
    )
    parser.add_argument("cmd", nargs=argparse.REMAINDER, help="Command to execute after `--`.")

    args = parser.parse_args(argv)
    cmd = list(args.cmd)
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        print("[harness_run] ERROR: no command supplied after `--`.", file=sys.stderr)
        return 2

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"{ts}_{sanitize_name(args.name)}.log"

    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")

    proc = subprocess.run(
        cmd,
        cwd=args.cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    raw_output = proc.stdout or ""
    log_path.write_text(raw_output, encoding="utf-8", newline="\n")

    lines = raw_output.splitlines()
    total_lines = len(lines)
    if args.filter_regex:
        pattern = re.compile(args.filter_regex)
        matched = [line for line in lines if pattern.search(line)]
        if matched:
            lines = matched

    max_lines = max(1, args.max_lines)
    truncated = len(lines) > max_lines
    tail_lines = lines[-max_lines:]

    rel_log = log_path.relative_to(REPO_ROOT).as_posix()
    print(
        f"[harness_run] name={args.name} exit={proc.returncode} "
        f"total_lines={total_lines} shown={len(tail_lines)} log={rel_log}"
    )
    if truncated:
        print(f"[harness_run] ... omitted {len(lines) - len(tail_lines)} earlier lines (see {rel_log}) ...")
    for line in tail_lines:
        print(line)

    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
