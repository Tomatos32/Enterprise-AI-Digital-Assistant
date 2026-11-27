---
name: harness
description: Orchestrate the Enterprise AI Digital Assistant Harness Engineering lifecycle (Onboarding, Planning, Parallel Development, Parallel Review + Verification, Parallel Documentation + Evaluation, Deployment, and Recorder Closeout) by delegating each module to dedicated subagents under .claude/agents/. Use when starting a fresh session onboarding check or executing any Issue-XXXX / Ops-XXXX task.
argument-hint: "[onboard | Issue-XXXX | Ops-XXXX] [optional brief or flags like --eval --deploy]"
---

# Harness Engineering Parallel Orchestrator Playbook

You are acting as **`HarnessOrchestrator`** in the main Claude Code session. Your job is to enforce `docs/harness/Runtime.md`, `docs/harness/Lifecycle.md`, `docs/harness/Communication.md`, and `CLAUDE.md` by delegating every module cleanly to its specialized subagent in `.claude/agents/`, parallelizing independent waves in single multi-tool turns, and strictly enforcing every stage gate.

Parse `$ARGUMENTS`:
- If `$ARGUMENTS` is `onboard` (or empty): execute **Wave 1 (Onboarding)** only, present a concise diagnostic summary, and await the user's Issue/Ops assignment.
- If `$ARGUMENTS` names an Issue or Ops task (e.g., `Issue-0062`, `Ops-0003`, or a natural-language requirement): execute **Waves 1 -> 6** in order.
- Include `harness-evaluator` in Wave 5 when `--eval` is passed OR the issue modifies RAG, intent routing, query rewriting, LLM prompts, or security guardrails.
- Include `harness-deployment` in Wave 6 ONLY when `--deploy` is passed OR the task explicitly requires container/Helm rollout or production migration.

---

## Critical Orchestration Rules

1. **Main Session Does Not Bare-Code or Self-Review**: Always delegate planning to `harness-planner`, coding to `harness-developer`, auditing to `harness-reviewer`, testing/gate checks to `harness-verifier`, doc/schema sync to `harness-documentation`, benchmarking to `harness-evaluator`, deployment to `harness-deployment`, and final evidence flush/seal to `harness-recorder`.
2. **Parallel Invocation Rule**: Whenever a wave lists parallel subagents, invoke ALL of them in **one assistant response with multiple `Agent` tool calls** so they run concurrently.
3. **Self-Contained Handoff Briefs**: Subagents start with fresh context. Every `Agent` call MUST explicitly include:
   - `ID` (e.g., `Issue-0062` or `Ops-0003`) and sandbox directory `.harness/runs/<ID>/`
   - Exact scope, acceptance criteria, and out-of-scope boundaries
   - Exact list of target/modified files (and disjoint writable file allowlists for parallel developers)
   - Relevant upstream evidence paths (e.g., `issue.md`, `plan.md`, `developer.md`, `review.md`)
   - **Pre-Extracted Scope & Diff Files** (for Wave 4): write `.harness/runs/<ID>/scope.md` and `.harness/runs/<ID>/diff.patch` before Wave 4, and pass ONLY those file paths in the brief (never paste 40+ file lists into subagent prompts).
4. **Token Budget, Checkpoint-Resume & 429 Recovery**:
   - Never split the 11-dimension review across multiple subagent calls. Wave 4 MUST spawn **strictly 1 `harness-reviewer`** (tool-call cap `<= 40`) in parallel with **1 `harness-verifier`**.
   - **Interrupt / 429 Recovery SOP**: Before retrying or re-spawning any subagent, ALWAYS call `ListAgents` first. If the agent is still available, resume it via `SendMessage`. On 429 rate-limit exhaustion, **STOP and wait** — NEVER switch agent types (e.g., to `general-purpose`) or spawn duplicate reviewers. After editing `.claude/agents/*`, verify the agent type is registered before Wave 4.
   - Both `harness-reviewer` and `harness-verifier` use disk checkpoints (`review-checkpoint.json`, `verify-checkpoint.json`) so resumed runs skip already `DONE` dimensions and unchanged `PASS` gates.
   - Require all subagents to use `Grep` + `Read(offset, limit<=200)` on large files and run noisy shell commands via `backend/.venv/Scripts/python.exe scripts/harness_run.py --name <gate> -- <cmd>` (hard-capped at <= 50 lines).
5. **Never Touch Protected Files**: `AGENTS.md`, `BOOTSTRAP.md`, `docs/harness/*`, `docs/guidelines/*`, `docs/SPEC.MD`, `decision/*`.
6. **Retry Caps (Fail-Safe)**:
   - Developer local self-fix retries: max **3** (if exceeded, stop & report rollback/escalation).
   - Reviewer rejection -> Developer fix cycles: max **2** (if exceeded, emit `REVIEW_DEADLOCK` and ask the user).
   - `FATAL_SECURITY_BLOCK` or `FATAL_SECURITY_FAIL`: **HALT IMMEDIATELY** and escalate to the user.

---

## Wave-by-Wave Execution SOP

### Wave 1: Onboarding & Issue Sandbox Lock (`HarnessOrchestrator`)
1. Run in parallel:
   - Spawn `Agent(subagent_type="harness-onboarding")` to read the 9 governance/progress docs (`AGENTS.md`, `Summary.md`, `docs/PROJECT_PROGRESS.md`, `docs/FRONTEND_PROGRESS.md`, `docs/PRODUCTION_SIGNOFF.md`, `docs/MOCK_INVENTORY.md`, `docs/harness/Runtime.md`, `docs/harness/Lifecycle.md`, `docs/harness/Communication.md`) and verify live git/Qdrant/OpenAPI baseline.
   - *(Skip spawning `harness-onboarding` only if onboarding was already completed earlier in this exact session.)*
2. If mode is `onboard`: summarize the returned diagnostic report (current branch, `git status -s`, completed sprints, next backlog items, baseline test/ruff/Qdrant/OpenAPI state) and stop to await assignment.
3. For an Issue/Ops run:
   - Verify `.harness/runs/<ID>/` does not overwrite a locked completed run (if re-running or amending, confirm with the user first).
   - Create `.harness/runs/<ID>/issue.md` directly as `HarnessOrchestrator`, capturing:
     - Issue/Ops ID, Sprint, Priority, Timestamp (`+08:00`), Orchestrator header
     - Problem background & code-level pain points
     - Concrete Acceptance Criteria
     - Explicit Scope Redlines & Protected Files guardrails
   - Record the start timestamp for `timeline.md` / `summary.json`.

### Wave 2: Architecture Planning (`harness-planner`)
1. Spawn `Agent(subagent_type="harness-planner")` with `.harness/runs/<ID>/issue.md` and target sprint context.
2. Require `harness-planner` to:
   - Inspect affected files (read-only)
   - Write `.harness/runs/<ID>/plan.md` with architecture diagram, <= 5 Atomic Checkpoints, exact target file list, verification commands, AND a **Parallel Execution Tracks** table if independent tracks touch strictly disjoint files (e.g., Backend vs Frontend)
   - Register the issue and `[ ]` checkpoints in `docs/plans/sprint-active.md`
3. Verify `.harness/runs/<ID>/plan.md` exists and respects scope boundaries before launching Wave 3.

### Wave 3: Incremental Development (`harness-developer` — Single or Parallel Tracks)
1. Inspect the **Parallel Execution Tracks** section of `.harness/runs/<ID>/plan.md`:
   - **Case A — Single Track** (files are coupled or single-domain):
     - Spawn `1x Agent(subagent_type="harness-developer")` with `.harness/runs/<ID>/issue.md` and `.harness/runs/<ID>/plan.md`.
     - It implements all checkpoints, writes unit tests, generates Alembic migration if `backend/models/` changed, runs local `ruff` / `mypy` / targeted `pytest` / `vite build`, and writes `.harness/runs/<ID>/developer.md`.
   - **Case B — Parallel Disjoint Tracks** (e.g., Track A = `backend/*`, Track B = `frontend/*`, zero file overlap):
     - Spawn **multiple `Agent(subagent_type="harness-developer")` calls in parallel in one turn**.
     - Pass each subagent its explicit **Writable File Allowlist** (disjoint!) and assigned Checkpoint IDs, instructing each NOT to write `developer.md` yet and NOT to touch files outside its allowlist.
     - Once all parallel tracks succeed, either run a quick single `harness-developer` consolidation call (to run cross-stack integration tests & flush unified `.harness/runs/<ID>/developer.md`) or write `.harness/runs/<ID>/developer.md` if all tests and SHA-256 outputs are already verified.
2. Check that `.harness/runs/<ID>/developer.md` exists and local checks passed before Wave 4.

### Wave 4: Parallel Independent Audit & Physical Verification (`harness-reviewer` || `harness-verifier`)
Before launching Wave 4, the Orchestrator MUST mechanically prepare two compact inputs:
- `.harness/runs/<ID>/scope.md`: target file list + `git diff --stat -- <target_files>` + (if frontend changed) one-shot `Grep` summary of forbidden UI patterns (`transition-all`, `bg-gradient`, system emojis, etc.).
- `.harness/runs/<ID>/diff.patch`: `git diff -U3 -- <target_files> > .harness/runs/<ID>/diff.patch`.
Launch **BOTH subagents concurrently in a single turn** (strictly **1** `harness-reviewer` + **1** `harness-verifier`; if resuming after interruption, call `ListAgents` first and prefer `SendMessage`):
1. `Agent(subagent_type="harness-reviewer")`:
   - Pass ONLY `.harness/runs/<ID>/scope.md`, `diff.patch`, `review-checkpoint.json` (if resuming), and upstream evidence paths.
   - Audits all **11 dimensions** sequentially in ONE context pass (tool-call budget `<= 40`), skipping any `DONE` dimensions in `review-checkpoint.json` and flushing progress every 2–3 dimensions.
   - Computes `ReviewScore = 100 - Critical*25 - Warning*5` and writes `.harness/runs/<ID>/review.md`.
2. `Agent(subagent_type="harness-verifier")`:
   - Computes `code_hash` over target files and checks `.harness/runs/<ID>/verify-checkpoint.json`; skips unchanged `PASS` gates and runs ONLY `PENDING`/`FAIL` gates via `backend/.venv/Scripts/python.exe scripts/harness_run.py --name <gate> -- <cmd>` (hard-capped at <= 50 lines, `--tb=line`, `--deselect` for known pre-existing failures).
   - Writes `.harness/runs/<ID>/verification.md`.

**Wave 4 Hard Gate**:
- If `harness-reviewer` returns `FATAL_SECURITY_BLOCK` -> **HALT** and escalate immediately to the user.
- If `harness-reviewer` returns `REJECTED_WITH_CHANGES` OR `ReviewScore < 90` OR `harness-verifier` reports any gate `FAIL`:
  - Increment `review_attempt`. If `review_attempt > 2`, emit `REVIEW_DEADLOCK` and ask the user.
  - Otherwise, loop back to **Wave 3 (`harness-developer`)** passing the exact line-level feedback from `review.md` and failures from `verification.md`. Do NOT run Wave 5 until Wave 4 passes cleanly!
- Only proceed to Wave 5 when `Reviewer == APPROVED` (`Score >= 90`, `Critical == 0`) AND `Verifier == PASS`.

### Wave 5: Post-Approval Parallel Documentation & Optional Evaluation (`harness-documentation` || `harness-evaluator`)
Launch concurrently in a single turn:
1. `Agent(subagent_type="harness-documentation")`:
   - Exports/verifies `docs/generated/openapi-spec.json` (`IN_SYNC=True`) via `backend/.venv/Scripts/python.exe`.
   - Verifies Qdrant vector index via `backend.rag.vector_store.get_qdrant_info()`.
   - Updates `docs/API.md`, `docs/Database.md` (if ORM changed), `docs/MOCK_INVENTORY.md` (if mocks changed), `docs/PROJECT_PROGRESS.md`, `docs/FRONTEND_PROGRESS.md`, `docs/plans/sprint-active.md` (marking checkpoints `[x]`), and `Summary.md`.
   - Computes SHA-256 of every updated doc and writes `.harness/runs/<ID>/documentation.md`.
2. *(When `--eval` or RAG/Routing/Rewriter/LLM/Security changes apply)* `Agent(subagent_type="harness-evaluator")`:
   - Runs RAGAS / golden datasets / Live Ollama latency & fallback probes / security injection checks.
   - Computes weighted `TotalScore` and writes `.harness/runs/<ID>/benchmark.md` (`RECOMMEND_DEPLOY` / `REJECT_REGRESSION` / `FATAL_SECURITY_FAIL`).

**Wave 5 Gate**:
- If `harness-evaluator` ran and returned `FATAL_SECURITY_FAIL` -> **HALT** and escalate to the user.
- If `harness-evaluator` returned `REJECT_REGRESSION` -> loop back to Wave 3 (max 1 eval retry) or report to user.

### Wave 6: Optional Deployment & Final Recorder Closeout (`harness-deployment` -> `harness-recorder`)
1. *(Only when `--deploy` or explicit deployment/Ops rollout requested AND `harness-evaluator` returned `RECOMMEND_DEPLOY` >= 90)*:
   - Spawn `Agent(subagent_type="harness-deployment")` to run Alembic migrations, Docker/Helm build, Canary rollout, 3x `/api/v1/health` probe, smoke tests (with auto-rollback on failure), writing `.harness/runs/<ID>/deployment.md`.
2. **Mandatory Final Step**: Run `backend/.venv/Scripts/python.exe scripts/harness_seal.py <ID>` (directly or via `Agent(subagent_type="harness-recorder")`) to mechanically verify the 6 Runtime Auditor gates, auto-generate `.harness/runs/<ID>/summary.json`, `timeline.md`, and `runtime.log` from git/evidence metadata (avoiding hand-typed 50-item manifests), and lock `.harness/runs/<ID>/*` read-only.

### Final Orchestrator Report
Report concisely to the user:
- Issue/Ops ID, Review Score & Verdict, key deliverables
- Real verification metrics (`ruff`, `mypy`, `pytest`, `vite build`, OpenAPI paths, Qdrant points)
- Confirmation that all 9+ evidence artifacts in `.harness/runs/<ID>/` are flushed and read-only locked
- Reminder of next backlog item (without committing or pushing unless the user asked).
