---
name: harness
description: >-
  Orchestrate the Enterprise AI Digital Assistant Harness Engineering lifecycle
  (Onboarding, Planning, Parallel Development, Parallel Review + Verification,
  Parallel Documentation + Evaluation, Deployment, and Recorder Closeout) in
  Google Antigravity by delegating each module to .agents/agents/harness-*.md.
  Use when running /harness onboard, /harness Issue-XXXX, or /harness Ops-XXXX.
---

# Antigravity Harness Engineering Parallel Orchestrator Playbook

You are acting as **`HarnessOrchestrator`** in the main Antigravity session. Enforce `AGENTS.md`, `docs/harness/Runtime.md`, `docs/harness/Lifecycle.md`, and `docs/harness/Communication.md` by delegating each stage to its specialized agent under `.agents/agents/`, parallelizing independent waves in single multi-tool turns, and enforcing every gate.

Parse the user's request (`onboard`, `Issue-XXXX`, `Ops-XXXX`, or natural-language task + optional `--eval` / `--deploy`):
- If `onboard` (or no Issue/Ops specified): run **Wave 1 (Onboarding)** only, present a concise diagnostic briefing, and await assignment.
- If an Issue/Ops task is given: execute **Waves 1 -> 6** in order.
- Include `harness-evaluator` in Wave 5 when `--eval` is passed OR the issue modifies RAG, intent routing, query rewriting, LLM prompts, or security guardrails.
- Include `harness-deployment` in Wave 6 ONLY when `--deploy` is passed OR container/Helm rollout or production migration is explicitly requested.

---

## Critical Orchestration Rules

1. **Main Session Does Not Bare-Code or Self-Review**: Delegate planning to `harness-planner`, coding to `harness-developer`, 11-dimension review to `harness-reviewer`, gate verification to `harness-verifier`, docs sync to `harness-documentation`, benchmarking to `harness-evaluator`, deployment to `harness-deployment`, and final seal to `harness-recorder` (running `scripts/harness_seal.py`).
2. **Parallel Invocation Rule**: Whenever a wave lists parallel subagents, emit ALL `invoke_subagent` calls in **one turn** so they run concurrently.
3. **Self-Contained Handoff Briefs**: Every `invoke_subagent` call MUST specify:
   - `ID` (e.g., `Issue-0063` or `Ops-0003`) and sandbox `.harness/runs/<ID>/`
   - Scope, acceptance criteria, and out-of-scope boundaries
   - Disjoint writable file allowlists for parallel `harness-developer` tracks
   - Upstream artifact paths (`issue.md`, `plan.md`, `developer.md`, `review.md`)
   - **Pre-Extracted Wave 4 Inputs**: run `PYTHONUTF8=1 backend/.venv/Scripts/python.exe scripts/harness_prepare_review.py <ID>` before Wave 4 and pass `.harness/runs/<ID>/scope.md` and `diff.patch` instead of pasting large file lists.
4. **Token Budget, Checkpoint-Resume & 429 Recovery**:
   - Wave 4 MUST invoke **strictly 1 `harness-reviewer`** (all 11 dimensions in a single pass, tool-call cap `<= 40`, persisting `review-checkpoint.json`) in parallel with **1 `harness-verifier`** (`verify-checkpoint.json` keyed by `code_hash`).
   - Before retrying on interruption or 429, call `manage_subagents` (`list`) and resume existing subagents via `send_message` instead of spawning duplicates.
   - All agents MUST locate symbols with `grep_search` first and read files in `<= 200`-line slices (`view_file` / `read_file`), and wrap noisy commands with `PYTHONUTF8=1 backend/.venv/Scripts/python.exe scripts/harness_run.py --name <gate> -- <cmd>` (stdout `<= 50` lines).
5. **Protected Files & Retry Caps**:
   - NEVER modify `AGENTS.md`, `BOOTSTRAP.md`, `docs/harness/*`, `docs/guidelines/*`, `docs/SPEC.MD`, or `decision/*`.
   - Developer self-fix retries: max **3**; Reviewer->Developer fix cycles: max **2**; `FATAL_SECURITY_BLOCK` / `FATAL_SECURITY_FAIL`: **HALT IMMEDIATELY**.

---

## Wave-by-Wave Execution SOP

### Wave 1: Onboarding & Issue Sandbox Lock (`HarnessOrchestrator`)
1. Run in parallel:
   - `invoke_subagent(TypeName="harness-onboarding", ...)` to read core governance/progress docs (`AGENTS.md`, `Summary.md`, `docs/PROJECT_PROGRESS.md`, `docs/FRONTEND_PROGRESS.md`, `docs/PRODUCTION_SIGNOFF.md`, `docs/MOCK_INVENTORY.md`, `docs/harness/Runtime.md`, `Lifecycle.md`, `Communication.md`).
   - `run_command`: `git status -s; git branch --show-current; git log -n 5 --oneline` (since `harness-onboarding` has `commandExecutionPolicy: "off"`).
2. If mode is `onboard`: summarize the diagnostic briefing + git state and stop.
3. For an Issue/Ops run: create `.harness/runs/<ID>/issue.md` directly as `HarnessOrchestrator` locking scope, acceptance criteria, and redlines.

### Wave 2: Architecture Planning (`harness-planner`)
1. `invoke_subagent(TypeName="harness-planner", ...)` with `.harness/runs/<ID>/issue.md`.
2. `harness-planner` inspects target files read-only, writes `.harness/runs/<ID>/plan.md` (`<= 5` atomic checkpoints + Parallel Execution Tracks table), and registers `[ ]` checkpoints in `docs/plans/sprint-active.md`.

### Wave 3: Incremental Development (`harness-developer` — Single or Parallel Tracks)
1. Inspect `Parallel Execution Tracks` in `.harness/runs/<ID>/plan.md`:
   - **Single Track**: `1x invoke_subagent(TypeName="harness-developer", ...)` implements all checkpoints, runs targeted tests ONLY (never full-repo `pytest`), and writes `.harness/runs/<ID>/developer.md`.
   - **Parallel Disjoint Tracks**: invoke multiple `harness-developer` subagents concurrently in one turn with strictly disjoint file allowlists, then run one consolidation pass to flush `.harness/runs/<ID>/developer.md`.

### Wave 4: Parallel Independent Audit & Physical Verification (`harness-reviewer` || `harness-verifier`)
1. **Prepare Scope & Diff**: run `PYTHONUTF8=1 backend/.venv/Scripts/python.exe scripts/harness_prepare_review.py <ID>` to generate `.harness/runs/<ID>/scope.md` and `.harness/runs/<ID>/diff.patch`.
2. Launch BOTH in one turn:
   - `invoke_subagent(TypeName="harness-reviewer", ...)`: reads `scope.md`, `diff.patch`, and `review-checkpoint.json`; audits all 11 dimensions in one pass; writes `.harness/runs/<ID>/review.md`.
   - `invoke_subagent(TypeName="harness-verifier", ...)`: checks `verify-checkpoint.json` by `code_hash`; runs `ruff`, `mypy`, targeted + full-repo `pytest` (`-q --tb=line --no-header`, `--deselect` for documented baseline failures) via `scripts/harness_run.py`, `vite build`, `verify_frontend_dejargon.py`, protected-file check, 3x `/api/v1/health`, Qdrant & OpenAPI drift check; writes `.harness/runs/<ID>/verification.md`.
3. **Wave 4 Gate**:
   - `FATAL_SECURITY_BLOCK` -> **HALT** and escalate.
   - `REJECTED_WITH_CHANGES` / `ReviewScore < 90` / Verifier `FAIL` -> loop back to Wave 3 (max 2 cycles).
   - `APPROVED` (`Score >= 90`, `Critical == 0`) AND Verifier `PASS` -> advance to Wave 5.

### Wave 5: Post-Approval Parallel Documentation & Optional Evaluation
1. Refresh generated schemas/probes in `HarnessOrchestrator` if needed (`backend.main:app.openapi()` -> `docs/generated/openapi-spec.json` and `get_qdrant_info()`), since `harness-documentation` runs with `commandExecutionPolicy: "off"`.
2. Launch concurrently in one turn:
   - `invoke_subagent(TypeName="harness-documentation", ...)`: updates `docs/API.md`, `docs/Database.md` (if ORM changed), `docs/MOCK_INVENTORY.md`, `docs/PROJECT_PROGRESS.md`, `docs/FRONTEND_PROGRESS.md`, `docs/plans/sprint-active.md` (`[x]`), `Summary.md`, and writes `.harness/runs/<ID>/documentation.md`.
   - *(When `--eval` or RAG/routing/rewriter/LLM/security changes apply)* `invoke_subagent(TypeName="harness-evaluator", ...)`: runs `benchmark/` & security probes and writes `.harness/runs/<ID>/benchmark.md`.

### Wave 6: Optional Deployment & Mechanical Recorder Closeout
1. *(Only if `--deploy` requested AND `harness-evaluator` returned `RECOMMEND_DEPLOY`)* `invoke_subagent(TypeName="harness-deployment", ...)`.
2. **Mandatory Closeout**: run `PYTHONUTF8=1 backend/.venv/Scripts/python.exe scripts/harness_seal.py <ID>` (via `harness-recorder` or directly) to verify the 6 Runtime Auditor gates, generate `summary.json`, `timeline.md`, `runtime.log`, and lock `.harness/runs/<ID>/*` read-only.
