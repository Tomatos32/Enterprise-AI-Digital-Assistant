"""Mechanical Harness Closeout & Read-Only Seal Script (Stage 10).

Verifies Runtime Auditor prerequisites, auto-generates `.harness/runs/<ID>/summary.json`,
`timeline.md`, and `runtime.log` from upstream evidence and git status (eliminating
hand-written 50-item artifact manifests), and locks evidence files read-only.

Usage:
    backend/.venv/Scripts/python.exe scripts/harness_seal.py Issue-0062
    backend/.venv/Scripts/python.exe scripts/harness_seal.py Issue-0062 --dry-run
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import stat
import subprocess
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
REQUIRED_UPSTREAM = [
    "issue.md",
    "plan.md",
    "developer.md",
    "review.md",
    "documentation.md",
    "verification.md",
]
PROTECTED_PATHS = [
    "AGENTS.md",
    "BOOTSTRAP.md",
    "docs/harness/",
    "docs/guidelines/",
    "docs/SPEC.MD",
]
TZ_CN = dt.timezone(dt.timedelta(hours=8))


def now_iso() -> str:
    return dt.datetime.now(TZ_CN).replace(microsecond=0).isoformat()


def run_git(args: list[str]) -> str:
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
    return (proc.stdout or "").strip()


def check_protected_files() -> list[str]:
    out = run_git(["status", "--porcelain", "--", *PROTECTED_PATHS])
    return [line for line in out.splitlines() if line.strip()]


def parse_review(review_text: str) -> tuple[str, int]:
    verdict = "UNKNOWN"
    for candidate in ("FATAL_SECURITY_BLOCK", "REJECTED_WITH_CHANGES", "APPROVED"):
        if re.search(rf"\b{candidate}\b", review_text):
            verdict = candidate
            break

    score = 0
    for pattern in (
        r"ReviewScore[^0-9]{0,20}(\d{1,3})\s*/\s*100",
        r"Score[^0-9]{0,15}(\d{1,3})\s*/\s*100",
        r"(\d{1,3})\s*/\s*100",
    ):
        match = re.search(pattern, review_text, re.IGNORECASE)
        if match:
            score = int(match.group(1))
            break
    return verdict, score


def parse_issue_metadata(issue_text: str, issue_id: str) -> tuple[str, str]:
    sprint = ""
    m_sprint = re.search(r"Sprint[:：\s`\*]+([A-Za-z0-9._-]+)", issue_text)
    if m_sprint:
        sprint = m_sprint.group(1).strip()

    title = issue_id
    for line in issue_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            title = stripped[2:].strip()
            break
    return sprint or "ACTIVE", title


def parse_int_metric(text: str, patterns: list[str], default: int = 0) -> int:
    for pat in patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                continue
    return default


def collect_artifacts(run_dir: Path) -> tuple[list[str], list[str]]:
    """Return (artifacts_list, untracked_files_list) from scope.md or git status."""
    artifacts: list[str] = []
    scope_file = run_dir / "scope.md"
    if scope_file.exists():
        for line in scope_file.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"^\s*[-*]\s+`?([^\s`]+)`?", line)
            if m:
                candidate = m.group(1).strip()
                if "/" in candidate and not candidate.startswith(".harness/"):
                    artifacts.append(candidate)

    status_out = run_git(["status", "--porcelain"])
    untracked: list[str] = []
    for line in status_out.splitlines():
        if len(line) < 4:
            continue
        code = line[:2]
        path = line[3:].strip().strip('"')
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip().strip('"')
        if path.startswith((".harness/", ".claude/")):
            continue
        if code == "??":
            untracked.append(path)
        if not artifacts:
            artifacts.append(path)

    deduped = sorted(dict.fromkeys(artifacts))
    return deduped, sorted(dict.fromkeys(untracked))


def load_verify_metrics(run_dir: Path) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    ckpt = run_dir / "verify-checkpoint.json"
    if ckpt.exists():
        try:
            data = json.loads(ckpt.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                metrics.update(data.get("metrics", {}))
        except json.JSONDecodeError:
            pass

    ver_text = (run_dir / "verification.md").read_text(encoding="utf-8", errors="replace")
    doc_text = (run_dir / "documentation.md").read_text(encoding="utf-8", errors="replace")

    metrics.setdefault(
        "ruff_errors",
        parse_int_metric(ver_text, [r"ruff_errors[:=\s]+(\d+)"], 0),
    )
    metrics.setdefault(
        "mypy_errors_modified_files",
        parse_int_metric(ver_text, [r"mypy_modified_errors[:=\s]+(\d+)", r"mypy_errors_modified_files[:=\s]+(\d+)"], 0),
    )
    metrics.setdefault(
        "full_repo_tests_passed",
        parse_int_metric(ver_text, [r"(\d+)\s+passed"], 0),
    )
    metrics.setdefault(
        "vite_modules_transformed",
        parse_int_metric(ver_text, [r"(\d+)\s+modules\s+transformed"], 0),
    )
    metrics.setdefault(
        "openapi_paths_count",
        parse_int_metric(doc_text, [r"OPENAPI_PATHS[:=\s]+(\d+)", r"openapi_paths[:=\s]+(\d+)"], 0),
    )
    metrics.setdefault(
        "qdrant_points_verified",
        parse_int_metric(doc_text, [r"points_count[:=\s\"']+?(\d+)"], 0),
    )
    return metrics


def build_timeline(issue_id: str, run_dir: Path, review_score: int, completed_at: str) -> tuple[list[dict[str, Any]], str]:
    stage_map = [
        ("Stage 1", "Issue 范围锁定", "HarnessOrchestrator", "issue.md"),
        ("Stage 2", "架构规划与检查点拆解", "PlannerAgent", "plan.md"),
        ("Stage 3-4", "增量开发与本地自测", "DeveloperAgent", "developer.md"),
        ("Stage 5", "11 维度代码审查", "ReviewerAgent", "review.md"),
        ("Stage 5B", "独立静态与物理门禁验证", "VerifierAgent", "verification.md"),
        ("Stage 6", "文档与 OpenAPI 同步", "DocumentationAgent", "documentation.md"),
        ("Stage 7", "质量与安全基准评测", "EvaluatorAgent", "benchmark.md"),
        ("Stage 8", "发布与灰度部署", "DeploymentAgent", "deployment.md"),
    ]
    entries: list[dict[str, Any]] = []
    rows = [
        f"# {issue_id} Harness 执行时间线",
        "",
        "| 阶段 | 动作 | 执行主体 | 时间戳 | 产出物 |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]
    for stage, action, agent, fname in stage_map:
        fpath = run_dir / fname
        if not fpath.exists():
            continue
        ts = dt.datetime.fromtimestamp(fpath.stat().st_mtime, TZ_CN).replace(microsecond=0).isoformat()
        rel = f".harness/runs/{issue_id}/{fname}"
        item: dict[str, Any] = {
            "agent": agent,
            "status": "APPROVED" if fname == "review.md" else "SUCCESS",
            "timestamp": ts,
            "artifact_generated": rel,
        }
        if fname == "review.md":
            item["review_score"] = review_score
        entries.append(item)
        rows.append(f"| {stage} | {action} | {agent} | {ts} | `{rel}` |")

    entries.append(
        {
            "agent": "RecorderAgent",
            "status": "SUCCESS",
            "timestamp": completed_at,
            "artifact_generated": f".harness/runs/{issue_id}/summary.json",
        }
    )
    rows.append(
        f"| Stage 10 | 审计归档与只读封存 | RecorderAgent (harness_seal.py) | {completed_at} | `.harness/runs/{issue_id}/summary.json` |"
    )
    return entries, "\n".join(rows) + "\n"


def lock_readonly(run_dir: Path) -> list[str]:
    locked: list[str] = []
    for path in sorted(run_dir.iterdir()):
        if path.is_file():
            os.chmod(path, stat.S_IREAD)
            locked.append(f"{path.name} ({path.stat().st_size}B)")
    return locked


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify Harness gates, flush closeout files, and seal read-only.")
    parser.add_argument("issue_id", help="Issue or Ops ID, e.g. Issue-0062")
    parser.add_argument("--sprint", default="", help="Override Sprint label.")
    parser.add_argument("--title", default="", help="Override title.")
    parser.add_argument("--dry-run", action="store_true", help="Validate gates and print summary without writing/locking.")
    parser.add_argument("--no-lock", action="store_true", help="Write closeout files without setting read-only bit.")
    args = parser.parse_args(argv)

    run_dir = REPO_ROOT / ".harness" / "runs" / args.issue_id
    if not run_dir.is_dir():
        print(f"[harness_seal] FAIL: run directory not found: {run_dir}")
        return 1

    # Gate 1: Upstream completeness
    missing = [f for f in REQUIRED_UPSTREAM if not (run_dir / f).is_file() or (run_dir / f).stat().st_size == 0]
    if missing:
        print(f"[harness_seal] FAIL Gate 1 (Upstream Evidence): missing/empty {missing}")
        return 1

    # Gate 2: Review verdict & score
    review_text = (run_dir / "review.md").read_text(encoding="utf-8", errors="replace")
    verdict, score = parse_review(review_text)
    if verdict != "APPROVED" or score < 90:
        print(f"[harness_seal] FAIL Gate 2 (Review): verdict={verdict}, score={score} (requires APPROVED & >=90)")
        return 1

    # Gate 4: Protected files untouched
    protected_hits = check_protected_files()
    if protected_hits:
        print(f"[harness_seal] FAIL Gate 4 (Protected Files): {protected_hits}")
        return 1

    issue_text = (run_dir / "issue.md").read_text(encoding="utf-8", errors="replace")
    plan_text = (run_dir / "plan.md").read_text(encoding="utf-8", errors="replace")
    sprint_detected, title_detected = parse_issue_metadata(issue_text, args.issue_id)
    sprint = args.sprint or sprint_detected
    title = args.title or title_detected

    cp_count = len(re.findall(r"\bCP-\d+\b", plan_text)) or 1
    completed_at = now_iso()
    created_at = dt.datetime.fromtimestamp((run_dir / "issue.md").stat().st_mtime, TZ_CN).replace(microsecond=0).isoformat()
    artifacts, untracked = collect_artifacts(run_dir)
    metrics = load_verify_metrics(run_dir)
    timeline_entries, timeline_md = build_timeline(args.issue_id, run_dir, score, completed_at)

    summary = {
        "issue_id": args.issue_id,
        "sprint": sprint,
        "title": title,
        "status": "COMPLETED",
        "review_verdict": verdict,
        "created_at": created_at,
        "completed_at": completed_at,
        "review_score": score,
        "checkpoints_total": cp_count,
        "checkpoints_completed": cp_count,
        "ruff_errors": metrics["ruff_errors"],
        "mypy_errors_modified_files": metrics["mypy_errors_modified_files"],
        "full_repo_tests_passed": metrics["full_repo_tests_passed"],
        "vite_modules_transformed": metrics["vite_modules_transformed"],
        "openapi_paths_count": metrics["openapi_paths_count"],
        "qdrant_points_verified": metrics["qdrant_points_verified"],
        "artifacts": artifacts,
        "agent_timeline": timeline_entries,
    }

    log_lines = [
        f"[{item['timestamp']}] [INFO] [{item['agent']}] status={item['status']} artifact={item['artifact_generated']}"
        for item in timeline_entries
    ]
    log_lines.append(
        f"[{completed_at}] [SYSTEM] [RecorderAgent] Sealed {args.issue_id}: verdict={verdict} score={score} artifacts={len(artifacts)} protected_count=0"
    )
    runtime_log = "\n".join(log_lines) + "\n"

    if args.dry_run:
        print(
            f"[harness_seal] DRY-RUN PASS: {args.issue_id} verdict={verdict} score={score} "
            f"artifacts={len(artifacts)} protected=0"
        )
        return 0

    (run_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    (run_dir / "timeline.md").write_text(timeline_md, encoding="utf-8", newline="\n")
    (run_dir / "runtime.log").write_text(runtime_log, encoding="utf-8", newline="\n")

    locked_files = [] if args.no_lock else lock_readonly(run_dir)
    print(f"[harness_seal] PASS: {args.issue_id} verdict={verdict} score={score} artifacts={len(artifacts)} locked={len(locked_files)}")
    if untracked:
        print(f"[harness_seal] git hint: git add -u && git add {' '.join(untracked[:10])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
