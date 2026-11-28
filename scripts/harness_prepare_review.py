#!/usr/bin/env python3
"""Pre-generate compact Wave 4 review inputs (`scope.md` and `diff.patch`).

Collects target files for an Issue/Ops run (from explicit CLI args, `plan.md`,
or `git status -s`), writes `.harness/runs/<ID>/scope.md` (with `git diff --stat`
and a one-shot frontend forbidden-pattern scan), and writes
`.harness/runs/<ID>/diff.patch` so `harness-reviewer` can audit all 11
dimensions without running unscoped `git diff` or opening dozens of files.

Usage:
    backend/.venv/Scripts/python.exe scripts/harness_prepare_review.py Issue-0063
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TZ_CN = dt.timezone(dt.timedelta(hours=8))
TARGET_PREFIXES = ("backend/", "frontend/", "scripts/", "tests/", "benchmark/", "docs/", "deployments/")
FRONTEND_FORBIDDEN_PATTERNS = [
    ("transition-all", re.compile(r"\btransition-all\b")),
    ("bg-gradient", re.compile(r"\bbg-gradient-")),
    ("TTFT leak", re.compile(r"TTFT\s*:")),
    ("Tokens leak", re.compile(r"Tokens\s*:\s*\d+")),
    ("LangGraph jargon", re.compile(r"LangGraph\s+interrupt|●\s*(?:ROUTER|TOOL)")),
    ("System emoji", re.compile(r"[💡⚠️⚙️✅❌🚀🔥]")),
]


def run_git(args: list[str]) -> tuple[int, str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return proc.returncode, proc.stdout or ""


def collect_files_from_plan(plan_path: Path) -> list[str]:
    if not plan_path.is_file():
        return []
    text = plan_path.read_text(encoding="utf-8", errors="replace")
    found: list[str] = []
    for match in re.finditer(r"`([A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+\.[A-Za-z0-9]+)`", text):
        candidate = match.group(1).strip()
        if candidate.startswith(TARGET_PREFIXES) and (REPO_ROOT / candidate).exists():
            found.append(candidate)
    return list(dict.fromkeys(found))


def collect_files_from_git() -> tuple[list[str], set[str]]:
    _rc, status_out = run_git(["status", "--porcelain"])
    files: list[str] = []
    untracked: set[str] = set()
    for line in status_out.splitlines():
        if len(line) < 4:
            continue
        code = line[:2]
        path = line[3:].strip().strip('"')
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip().strip('"')
        if path.startswith((".harness/", ".claude/", ".opencode/", ".agents/")):
            continue
        if not path.startswith(TARGET_PREFIXES):
            continue
        files.append(path)
        if code == "??":
            untracked.add(path)
    return list(dict.fromkeys(files)), untracked


def scan_frontend_patterns(target_files: list[str]) -> list[str]:
    fe_files = [f for f in target_files if f.startswith("frontend/") and f.endswith((".vue", ".ts", ".js", ".tsx", ".jsx", ".css"))]
    hits: list[str] = []
    for rel in fe_files:
        fpath = REPO_ROOT / rel
        if not fpath.is_file():
            continue
        for idx, line in enumerate(fpath.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
            for label, pattern in FRONTEND_FORBIDDEN_PATTERNS:
                if pattern.search(line):
                    hits.append(f"- `{rel}:{idx}` [{label}]: `{line.strip()[:100]}`")
    return hits


def build_diff_patch(target_files: list[str], untracked: set[str], max_lines: int) -> tuple[str, int]:
    tracked = [f for f in target_files if f not in untracked]
    chunks: list[str] = []
    if tracked:
        _rc, diff_out = run_git(["diff", "-U3", "--", *tracked])
        if diff_out.strip():
            chunks.append(diff_out.rstrip("\n"))

    for rel in sorted(untracked & set(target_files)):
        fpath = REPO_ROOT / rel
        if not fpath.is_file():
            continue
        _rc, udiff = run_git(["diff", "--no-index", "-U3", "--", "/dev/null", rel])
        if udiff.strip():
            chunks.append(udiff.rstrip("\n"))

    combined = "\n".join(chunks) + ("\n" if chunks else "")
    lines = combined.splitlines()
    if max_lines > 0 and len(lines) > max_lines:
        omitted = len(lines) - max_lines
        combined = "\n".join(lines[:max_lines]) + f"\n# ... truncated {omitted} lines (exceeded --max-diff-lines {max_lines}) ...\n"
    return combined, len(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("issue_id", help="Issue or Ops ID, e.g. Issue-0063")
    parser.add_argument("--files", nargs="*", default=[], help="Explicit relative target file paths.")
    parser.add_argument("--max-diff-lines", type=int, default=2000, help="Cap diff.patch lines (default: 2000, 0=unlimited).")
    args = parser.parse_args(argv)

    run_dir = REPO_ROOT / ".harness" / "runs" / args.issue_id
    if not run_dir.is_dir():
        print(f"[harness_prepare_review] ERROR: run directory not found: {run_dir}", file=sys.stderr)
        return 1

    git_files, untracked = collect_files_from_git()
    if args.files:
        target_files = list(dict.fromkeys(f.replace("\\", "/") for f in args.files))
    else:
        plan_files = collect_files_from_plan(run_dir / "plan.md")
        target_files = list(dict.fromkeys([*git_files, *plan_files]))

    diff_stat = ""
    tracked = [f for f in target_files if f not in untracked]
    if tracked:
        _rc, diff_stat = run_git(["diff", "--stat", "--", *tracked])

    fe_hits = scan_frontend_patterns(target_files)
    patch_text, total_patch_lines = build_diff_patch(target_files, untracked, args.max_diff_lines)

    now = dt.datetime.now(TZ_CN).replace(microsecond=0).isoformat()
    scope_lines = [
        f"# {args.issue_id} Review Scope",
        "",
        f"- Generated: `{now}`",
        f"- Target Files: `{len(target_files)}`",
        f"- Diff Patch Lines: `{total_patch_lines}`",
        "",
        "## Target Files",
    ]
    if target_files:
        for rel in target_files:
            tag = " *(new)*" if rel in untracked else ""
            scope_lines.append(f"- `{rel}`{tag}")
    else:
        scope_lines.append("- *(none detected)*")

    scope_lines.extend(["", "## Git Diff Stat", "```text", diff_stat.strip() or "(no tracked diff)", "```"])
    scope_lines.extend(["", "## Frontend Forbidden-Pattern Scan"])
    if fe_hits:
        scope_lines.extend(fe_hits[:30])
    else:
        scope_lines.append("- `0` hits")

    scope_path = run_dir / "scope.md"
    patch_path = run_dir / "diff.patch"
    scope_path.write_text("\n".join(scope_lines) + "\n", encoding="utf-8", newline="\n")
    patch_path.write_text(patch_text, encoding="utf-8", newline="\n")

    print(
        f"[harness_prepare_review] OK: {args.issue_id} files={len(target_files)} "
        f"diff_lines={total_patch_lines} fe_hits={len(fe_hits)} "
        f"scope={scope_path.relative_to(REPO_ROOT).as_posix()} patch={patch_path.relative_to(REPO_ROOT).as_posix()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
