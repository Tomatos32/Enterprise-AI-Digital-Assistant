# CLAUDE.md - Enterprise AI Digital Assistant Harness Control Plane

> **Repository**: Enterprise AI Digital Assistant (`FastAPI + LangGraph + LangChain + Qdrant + MySQL + Redis + Celery + WebSocket + Vue3`)
> **Governance Root**: [AGENTS.md](AGENTS.md) | **Latest Handover**: [Summary.md](Summary.md) | **Runtime Kernel**: [docs/harness/Runtime.md](docs/harness/Runtime.md)

Every Claude Code session opened in this repository acts as the **HarnessOrchestrator**. Direct freeform coding without Harness evidence tracking is prohibited. Delegate each Harness module to its dedicated project subagent under `.claude/agents/` and invoke independent modules in parallel.

---

## 1. Strict Invariants (Non-Negotiable Redlines)

1. **Mandatory Evidence Sandbox**: Never edit application code (`backend/`, `frontend/`) before creating `.harness/runs/<Issue-XXXX>/issue.md` (or `Ops-XXXX/issue.md`) and `.harness/runs/<Issue-XXXX>/plan.md`. Every Issue/Ops run must produce all 9 core evidence files under `.harness/runs/<ID>/`: `issue.md`, `plan.md`, `developer.md`, `review.md`, `documentation.md`, `verification.md`, `summary.json`, `timeline.md`, `runtime.log` (plus `benchmark.md` / `deployment.md` in Dev/Release mode). Never store evidence outside the repo's `.harness/runs/` directory.
2. **Python Virtual Environment**: ALWAYS use `backend/.venv/Scripts/python.exe` (with `PYTHONUTF8=1`). NEVER invoke system global `python` or `pytest`.
3. **Human-Only Protected Files**: NEVER modify `AGENTS.md`, `BOOTSTRAP.md`, `docs/harness/*`, `docs/guidelines/*`, `docs/SPEC.MD`, or accepted ADRs under `decision/`. If changes are needed, emit a `.draft.md` note for human review.
4. **No Fabricated Verification**: Never claim lint, typecheck, test, or build passed without running the actual commands and recording real stdout + exit codes:
   - `backend/.venv/Scripts/python.exe -m ruff check backend/ benchmark/` (0 errors)
   - `backend/.venv/Scripts/python.exe -m mypy --explicit-package-bases --follow-imports=skip --ignore-missing-imports <modified_py_files>` (0 errors)
   - `backend/.venv/Scripts/python.exe -m pytest <targeted_suites>` and `backend/.venv/Scripts/python.exe -m pytest backend/tests/ -q --tb=short` (0 new regressions; converge to 100% pass)
   - `frontend/`: `npm run build` (`vite build`, 0 errors) + `backend/.venv/Scripts/python.exe scripts/verify_frontend_dejargon.py`
5. **No Frontend Hardcoded Business Parameters**: Never hardcode fake business args (product names, quantities, prices) in frontend components. All tool and approval slots must be extracted by backend logic from real user input + multi-turn context, asking natural-language clarifying questions when required slots are missing.
6. **Low-Latency Non-Thinking Internal LLM & Zero Leak**: Intent routing and query rewriting LLM calls MUST use non-thinking paths (`thinking=False`, `streaming=False`), strict timeout control, deterministic offline fallback (`local_fallback` / no-internet unit tests must pass), and stream isolation (`callbacks=[]`, internal node/tag filtering). Never leak routing tags, sub-queries, JSON payloads, or debug jargon into the employee UI.
7. **Strict RBAC & Secret Isolation**: Never expose admin LLM settings, node configs, document upload/ingestion, or system telemetry/monitoring controls in the employee (`employee`) view. Never return plaintext API Keys or Secret Keys from any endpoint.
8. **Zero System Emoji & De-Jargon UI**: Never place system emojis in frontend UI or backend user-facing labels. Use `lucide-vue-next` and `@hugeicons/vue` vector icons exclusively.
9. **Dual-Theme WCAG AA/AAA Fidelity**: Preserve warm-white Light mode (contrast >= 7:1) and obsidian Dark mode (contrast >= 4.5:1).
10. **Scope Lock (Do Not Expand Scope)**: Do not implement excluded/deferred items unless explicitly re-authorized by the user:
    - `[EXCLUDED]` 4-level security clearance UI switcher and clearance-level filtering demos.
    - `[DEFERRED]` External workflow platform UI (`/workflows` Dify/N8N visual editor).
    - `[DEFERRED]` Feedback annotation & DPO export workbench (`/eval`, `/feedback`).

---

## 2. Subagent Registry (`.claude/agents/`)

| Subagent Name | Model | Harness Module / Role | Primary Output Artifact | Mutability / Isolation |
| :--- | :---: | :--- | :--- | :--- |
| `harness-onboarding` | `haiku` | Phase 1: Onboarding & Baseline Diagnostician | Structured diagnostic report (returned to Orchestrator) | Read-only (no Write/Edit) |
| `harness-planner` | `sonnet` | Stage 2: Architecture Planner & Track Decomposer | `.harness/runs/<ID>/plan.md` + `docs/plans/sprint-active.md` | Plan & sprint board only (never edits code) |
| `harness-developer` | `sonnet` | Stage 3 & 4: Full-Stack Developer & Self-Tester | Source code, tests, migrations + `.harness/runs/<ID>/developer.md` | Full dev tools; supports parallel disjoint tracks |
| `harness-reviewer` | `haiku` | Stage 5: Independent 11-Dimension Code Reviewer | `.harness/runs/<ID>/review.md` (`APPROVED` >= 90 required) | Read-only on code (`Edit` disabled) |
| `harness-verifier` | `haiku` | Stage 5B: Static, Test, Build & Physical Verifier | `.harness/runs/<ID>/verification.md` | Read-only on code (`Edit` disabled) |
| `harness-documentation` | `haiku` | Stage 6: Knowledge, OpenAPI & Qdrant Syncer | `docs/generated/openapi-spec.json`, repo docs + `documentation.md` | Docs & generated schemas only (never edits code) |
| `harness-evaluator` | `haiku` | Stage 7 (Dev/Eval): RAGAS, TTFT & Security Benchmarker | `.harness/runs/<ID>/benchmark.md` | Read-only on code (`Edit` disabled) |
| `harness-deployment` | `haiku` | Stage 8 (Release/Ops): Migration, Canary & Rollback Ops | `.harness/runs/<ID>/deployment.md` | Ops & probes only (`Edit` disabled) |
| `harness-recorder` | `haiku` | Stage 10: Runtime Auditor, Telemetry Flush & Seal | `summary.json`, `timeline.md`, `runtime.log` + read-only lock | Evidence & closeout metadata only |

---

## 3. Parallel Orchestration DAG (How to Run Every Issue / Ops Task)

Because Claude Code subagents cannot spawn nested subagents, **the main session IS `HarnessOrchestrator`**. Invoke `/harness <Issue-XXXX | Ops-XXXX | onboard>` (or follow this 6-Wave DAG directly) and emit parallel `Agent` tool calls in a single turn wherever a wave allows concurrency:

```text
Wave 1 [Onboarding - New Window]:
  └─ Parallel: harness-onboarding (reads 9 core docs + baseline) || git status -s check
  └─ Orchestrator creates .harness/runs/<ID>/issue.md (locks scope & acceptance criteria)

Wave 2 [Planning]:
  └─ harness-planner -> writes plan.md (<=5 atomic Checkpoints + Parallel Track Map) & patches sprint-active.md

Wave 3 [Development - Parallelizable on Disjoint Tracks]:
  ├─ Single module: 1x harness-developer -> edits code, runs local ruff/mypy/pytest/vite, writes developer.md
  └─ Multi-module (disjoint files, e.g. Backend + Frontend):
       Parallel: harness-developer (Track A: backend/*) || harness-developer (Track B: frontend/*)
       -> Consolidate cross-module integration test + developer.md

Wave 4 [Parallel Quality Gate - ZERO Race Condition]:
  ├─ Parallel: harness-reviewer (11-dim audit -> review.md)
  └─ Parallel: harness-verifier (ruff, mypy, pytest, vite build, dejargon, emoji, protected-file, health, SHA-256 -> verification.md)
  ── GATE ──
  • FATAL_SECURITY_BLOCK -> HALT immediately & escalate to human.
  • REJECTED_WITH_CHANGES / Score < 90 / Verifier FAIL -> Loop back to Wave 3 harness-developer (Max 2 review loops / Max 3 dev self-retries).
  • APPROVED (Score >= 90, Critical = 0) AND Verifier PASS -> Advance to Wave 5.

Wave 5 [Post-Approval Parallel Sync & Optional Eval - ZERO Race Condition]:
  ├─ Parallel: harness-documentation (OpenAPI export, Qdrant verify, docs sync, sprint-active [x], Summary.md -> documentation.md)
  └─ Parallel (when RAG/LLM/routing benchmark or Dev/Release mode applies): harness-evaluator (RAGAS/TTFT/security -> benchmark.md)
  ── GATE ──
  • Evaluator REJECT_REGRESSION / FATAL_SECURITY_FAIL -> Block closeout/deploy & loop back or escalate.

Wave 6 [Optional Deployment -> Final Recorder Seal]:
  ├─ (Only if release/Ops rollout requested AND Evaluator == RECOMMEND_DEPLOY): harness-deployment -> deployment.md
  └─ harness-recorder -> runs 6 Runtime Auditor gates, flushes summary.json, timeline.md, runtime.log, locks .harness/runs/<ID>/* read-only
```

---

## 4. Quick Onboarding & Task Entry

- Run `/harness onboard` in any fresh window to diagnose repository state without polluting main context.
- Run `/harness Issue-XXXX` (or any Issue/Ops ID) to execute the full 6-Wave Harness lifecycle with automatic parallel subagent dispatch.
- Never self-review code you wrote in the main session: always delegate review to `harness-reviewer` and verification to `harness-verifier`.

---

## 5. Token Budget & Output Noise-Reduction Rules (强制降噪与断点续跑规范)

To prevent 150k+ large-file context bloat, 272k Auto-Compact cache invalidation, 50k+ terminal log overflow, and wasted retries on rate limits, ALL orchestrator turns and subagents MUST obey these 5 hard rules:

1. **Sliced File Reading & Pre-Extracted Diff/Scope (斩断大文件重复读取)**:
   - **Prohibit full-file `Read` on large files (> 200 lines)** or generated artifacts (`docs/generated/openapi-spec.json`, `Summary.md`, `docs/PROJECT_PROGRESS.md`, `docs/FRONTEND_PROGRESS.md`, large `.py`/`.vue` modules).
   - Always use `Grep` first to locate target symbols/line numbers, then call `Read` with explicit `offset` and `limit` (100–200 lines per call).
   - Before Wave 4, `HarnessOrchestrator` MUST pre-generate `.harness/runs/<ID>/scope.md` (target file list + optional frontend forbidden-pattern `Grep` summary) and `.harness/runs/<ID>/diff.patch` (`git diff -U3 -- <target_files>`). Subagent prompts MUST point to these files instead of pasting 40+ file lists or running unscoped `git diff`.
2. **Single-Pass 11-Dimension Audit & Checkpoint-Resume (断点续跑 + 防 429 重复拉起)**:
   - NEVER spawn 11 separate subagents per dimension; Wave 4 MUST invoke **strictly 1 `harness-reviewer`** (tool-call cap `<= 40`) and **1 `harness-verifier`**.
   - **Interrupt / 429 Recovery**: Before retrying or spawning any subagent, ALWAYS call `ListAgents` first. If an agent already exists, resume it via `SendMessage` instead of spawning a duplicate. On 429 rate-limit exhaustion, **STOP and wait** — NEVER switch to `general-purpose` or re-spawn duplicates.
   - **Disk Checkpoints**: `harness-reviewer` persists `.harness/runs/<ID>/review-checkpoint.json` every 2–3 dimensions; `harness-verifier` persists `.harness/runs/<ID>/verify-checkpoint.json` keyed by `code_hash`. On resume, skip all `DONE` dimensions and unchanged `PASS` gates.
3. **Hard-Capped Command Wrapper & Tiered Gates (命令硬截断与门禁分层)**:
   - `harness-developer` runs **targeted tests ONLY** (never full-repo `pytest`). Full-repo `pytest` runs ONCE in `harness-verifier` (skipped if `code_hash` is unchanged).
   - Run noisy commands (`pytest`, `ruff`, `mypy`, `npm run build`) via `backend/.venv/Scripts/python.exe scripts/harness_run.py --name <gate> -- <cmd>`, which saves full logs to `.harness/logs/` and hard-caps stdout to **<= 50 lines** (<= 2k tokens).
   - Use `pytest -q --tb=line --no-header` and `--deselect` for documented pre-existing baseline failures (expand `--tb=short` only for NEW failures). Reports MUST list only failed `file:line`, exit codes, and concise summaries—never paste raw logs.
   - A `PreToolUse` hook in `.claude/settings.json` reinforces stdout truncation on `Bash` and `PowerShell` calls.
4. **Compact Edits & Mechanical Closeout (避免大块 Edit 与手写清单)**:
   - Keep `Edit` `old_string` short and unique (never paste entire Vue `<template>` blocks or full ASCII progress tables); use targeted scripts/`sed` for repetitive mechanical replacements.
   - Use `backend/.venv/Scripts/python.exe scripts/harness_seal.py <ID>` to mechanically generate `summary.json`, `timeline.md`, `runtime.log` and apply the read-only seal instead of hand-writing 50-item artifact manifests.
5. **Advisor Call Budget**:
   - Call `advisor` at most once before starting substantive work (when context is small), not at closeout when context is bloated.
