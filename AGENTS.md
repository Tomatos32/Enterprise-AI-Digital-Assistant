# AGENTS.md - Master Harness Navigation & Routing Map

> **Target System**: Enterprise AI Digital Assistant  
> **Tech Stack**: FastAPI + LangGraph + LangChain + Qdrant + MySQL + Redis + Celery + WebSocket + Vue3  
> **Harness Engine**: Self-Developing Multi-Agent Architecture (V1.0)  
> **Current Operating Mode**: [BOOTSTRAP.md](file:///g:/LLM_Learning/product/BOOTSTRAP.md) (System Infrastructure Initialization Mode)  
> **Supreme Runtime Specification**: [Runtime.md](file:///g:/LLM_Learning/product/docs/harness/Runtime.md) (Repository Runtime Kernel)  

---

## 1. Master Harness Compliance Rules (核心硬性合规守则)

ALL agents operating within this repository MUST strictly comply with the following master specifications:
1. **Supreme Runtime Kernel**: [docs/harness/Runtime.md](file:///g:/LLM_Learning/product/docs/harness/Runtime.md) (Execution Invariants & Mandatory Artifacts)
2. **Runtime Evidence Arch**: [docs/harness/evidence-design.md](file:///g:/LLM_Learning/product/docs/harness/evidence-design.md) (`.harness/runs/` Evidence Chain Spec)
3. **Harness Recorder Spec**: [docs/harness/recorder-design.md](file:///g:/LLM_Learning/product/docs/harness/recorder-design.md) (Telemetry & Auto Logs Spec)
4. **Operating Mode Spec**: [BOOTSTRAP.md](file:///g:/LLM_Learning/product/BOOTSTRAP.md) (Bootstrap Mode Rules & Exit Criteria)
5. **Master Harness Architecture**: [docs/harness/Harness.md](file:///g:/LLM_Learning/product/docs/harness/Harness.md)
6. **Multi-Agent Communication Protocol**: [docs/harness/Communication.md](file:///g:/LLM_Learning/product/docs/harness/Communication.md)
7. **Issue SDLC Lifecycle (10 Stages)**: [docs/harness/Lifecycle.md](file:///g:/LLM_Learning/product/docs/harness/Lifecycle.md)

---

## 2. Repository as Source of Truth

- **No Hidden Prompts**: All engineering rules, schemas, ADRs, and workflows are written in Git.
- **Minimal Portal Strategy**: This document (`AGENTS.md`) is a navigation map (<300 lines). Agents MUST load targeted rulebooks on demand.
- **Permissions Matrix**:
  - `AGENTS.md`, `BOOTSTRAP.md`, `docs/harness/*`, `docs/guidelines/*`, `docs/SPEC.MD` & accepted ADRs under `decision/*`: **HUMAN-ONLY / PROHIBITED FROM DIRECT AGENT EDITS** (emit a separate `.draft.md` note if updates are needed).
  - `docs/generated/*`: **AI 100% AUTO-MAINTAINED**.
  - `docs/plans/sprint-active.md`: **AI DYNAMIC TASK STATUS PATCHING ONLY**.

---

## 3. Reading Priority (Agent 文档读取优先级)

```text
Level 1: AGENTS.md, BOOTSTRAP.md, Runtime.md, evidence-design.md, recorder-design.md (Master Portal, Kernel & Evidence)
   │
   ▼
Level 2: docs/harness/Harness.md, Communication.md, Lifecycle.md (Protocol & SDLC)
   │
   ▼
Level 3: docs/guidelines/*.md & docs/harness/*-design.md (Agent Design Specs & Standards)
   │
   ▼
Level 4: docs/Architecture.md, Database.md, API.md (System Specifications)
   │
   ▼
Level 5: docs/memory/system-context.md & bug-history.md (Domain Context & Past Post-Mortems)
   │
   ▼
Level 6: docs/plans/sprint-active.md & docs/generated/* (Active Task Plan & Auto Schemas)
```

---

## 4. Agent Control Plane & Navigation Index (Agent 导航矩阵)

| Agent Name | Design Spec | System Prompt | Execution Playbook | Evidence Artifact |
| :--- | :--- | :--- | :--- | :--- |
| **Bootstrap Orchestrator**| [BOOTSTRAP.md](file:///g:/LLM_Learning/product/BOOTSTRAP.md) | [BOOTSTRAP.md](file:///g:/LLM_Learning/product/BOOTSTRAP.md) | [BOOTSTRAP.md](file:///g:/LLM_Learning/product/BOOTSTRAP.md) | `issue.md` & `summary.json` |
| **Planner Agent** | [planner-design.md](file:///g:/LLM_Learning/product/docs/harness/planner-design.md) | [planner-prompt.md](file:///g:/LLM_Learning/product/docs/harness/planner-prompt.md) | [planner-playbook.md](file:///g:/LLM_Learning/product/docs/harness/planner-playbook.md) | `plan.md` |
| **Developer Agent** | [developer-design.md](file:///g:/LLM_Learning/product/docs/harness/developer-design.md) | [developer-prompt.md](file:///g:/LLM_Learning/product/docs/harness/developer-prompt.md) | [developer-playbook.md](file:///g:/LLM_Learning/product/docs/harness/developer-playbook.md) | `developer.md` |
| **Reviewer Agent** | [reviewer-design.md](file:///g:/LLM_Learning/product/docs/harness/reviewer-design.md) | [reviewer-prompt.md](file:///g:/LLM_Learning/product/docs/harness/reviewer-prompt.md) | [reviewer-playbook.md](file:///g:/LLM_Learning/product/docs/harness/reviewer-playbook.md) | `review.md` |
| **Doc Agent** | [documentation-design.md](file:///g:/LLM_Learning/product/docs/harness/documentation-design.md) | [documentation-prompt.md](file:///g:/LLM_Learning/product/docs/harness/documentation-prompt.md) | [documentation-playbook.md](file:///g:/LLM_Learning/product/docs/harness/documentation-playbook.md) | `documentation.md` |
| **Evaluator Agent**| [evaluator-design.md](file:///g:/LLM_Learning/product/docs/harness/evaluator-design.md) | [evaluator-prompt.md](file:///g:/LLM_Learning/product/docs/harness/evaluator-prompt.md) | [scorecard.md](file:///g:/LLM_Learning/product/docs/harness/scorecard.md) | `benchmark.md` *(Dev Mode)* |
| **Deployment Agent**| [deployment-design.md](file:///g:/LLM_Learning/product/docs/harness/deployment-design.md) | [deployment-prompt.md](file:///g:/LLM_Learning/product/docs/harness/deployment-prompt.md) | [deployment-playbook.md](file:///g:/LLM_Learning/product/docs/harness/deployment-playbook.md) | `deployment.md` *(Dev Mode)* |

---

## 5. Development Rules & Guidelines Index

- **Supreme Runtime Kernel**: [Runtime.md](file:///g:/LLM_Learning/product/docs/harness/Runtime.md), [evidence-design.md](file:///g:/LLM_Learning/product/docs/harness/evidence-design.md) & [recorder-design.md](file:///g:/LLM_Learning/product/docs/harness/recorder-design.md)
- **Operating Mode**: [BOOTSTRAP.md](file:///g:/LLM_Learning/product/BOOTSTRAP.md)
- **Coding Standards**: [docs/guidelines/coding-standards.md](file:///g:/LLM_Learning/product/docs/guidelines/coding-standards.md)
- **LangGraph Agent Design**: [docs/guidelines/agent-design.md](file:///g:/LLM_Learning/product/docs/guidelines/agent-design.md)
- **RAG & Vector Standards**: [docs/guidelines/rag-standards.md](file:///g:/LLM_Learning/product/docs/guidelines/rag-standards.md)

---

## 6. Definition of Done (DoD)

Before declaring any task complete, ALL of the following criteria MUST be met with real stdout + exit codes (NEVER fabricate verification):

1. `PYTHONUTF8=1 backend/.venv/Scripts/python.exe -m ruff check backend/ benchmark/` returns ZERO errors.
2. `PYTHONUTF8=1 backend/.venv/Scripts/python.exe -m mypy --explicit-package-bases --follow-imports=skip --ignore-missing-imports <modified_py_files>` returns ZERO errors.
3. Targeted tests and `PYTHONUTF8=1 backend/.venv/Scripts/python.exe -m pytest backend/tests/ -q --tb=short --no-header` pass with zero new regressions.
4. When `frontend/` changes: `npm run build` (`vite build`, 0 errors) + `PYTHONUTF8=1 backend/.venv/Scripts/python.exe scripts/verify_frontend_dejargon.py` pass.
5. Alembic Migration script exists in `backend/migrations/versions/` if ORM models changed.
6. Reviewer Agent outputs `APPROVED` status with Scorecard >= 90 (written to `review.md`).
7. Documentation Agent exports updated OpenAPI JSON & Qdrant vector index.
8. Active Task checkpoint marked `[x]` in `docs/plans/sprint-active.md`.
9. Harness Recorder flushes `.harness/runs/<ID>/` evidence package (`summary.json`, `timeline.md`, `runtime.log`) via `scripts/harness_seal.py <ID>`.

---

## 7. Repository Structure Map

```text
enterprise-ai-agent/
├── AGENTS.md                             # [ROOT] Master Harness Navigation Map (This File)
├── BOOTSTRAP.md                          # [ROOT] Bootstrap Mode Operating Specification
├── .agents/                              # [Antigravity] Subagents, /harness Skill & Hooks
│   ├── agents/                           # Native Subagent Configs (harness-*.md)
│   ├── skills/harness/SKILL.md           # Native /harness Orchestration Playbook
│   └── hooks.json                        # Native SessionStart & PreToolUse Guards
├── .claude/                              # [Claude Code] Subagents, Settings & /harness Skill
├── .opencode/                            # [OpenCode] Synced Subagent Configs
├── backend/                              # [Pair-Coding] Python Backend (FastAPI + LangGraph)
├── frontend/                             # [Pair-Coding] Vue3 / NuxtJS Frontend
├── docs/                                 # [Long-Term] System Docs & Specifications
│   ├── Architecture.md                   # System Topology & Architecture Spec
│   ├── Database.md                       # MySQL ERD & Table Specifications
│   ├── API.md                            # OpenAPI & WebSocket Specification
│   ├── Workflow.md                       # LangGraph State Machine & SOP Flow
│   ├── Deployment.md                     # Docker / K8s / vLLM Operations Guide
│   ├── Plan.md                           # 12-Sprint Project Master Plan
│   ├── harness/                          # Harness Core Protocol Specifications
│   │   ├── Runtime.md                    # Supreme Harness Runtime Kernel Specification
│   │   ├── evidence-design.md            # .harness/runs/ Evidence Chain Design Spec
│   │   ├── recorder-design.md            # Harness Recorder Architecture Spec
│   │   ├── Harness.md                    # Master Harness Architecture
│   │   ├── Communication.md              # Multi-Agent Message Passing Protocol
│   │   ├── Lifecycle.md                  # Issue 10-Stage SDLC Lifecycle
│   │   └── *-design.md & *-playbook.md   # Agent Specs & Playbooks
│   └── guidelines/                       # Coding & Architecture Standards
├── .harness/                             # [Runtime Evidence] Issue 沙盒运行证据链包
│   └── runs/                             # Issue-XXXX/ 证据文件夹 (Read-Only)
├── memory/                               # [Long-Term] system-context.md & bug-history.md
├── decision/                             # [Long-Term] ADRs (0001-langgraph-state-machine.md)
├── plans/                                # [Dynamic] roadmap.md & sprint-active.md
├── generated/                            # [AI Auto] openapi-spec.json & db-schema.md
├── prompt/                               # [Human-Only] Prompt Templates & Guardrails
├── agents/                               # [Human-Only] Harness Subagent Configs
├── workflow/                             # [Human-Only] AST Scripts & Git Hooks
├── benchmark/                            # [Pair-Coding] RAGAS Datasets & Scripts
├── logs/                                 # [Runtime Data] Trajectories & Audit Logs (.gitignore)
└── .github/                              # [Human-Only] CI/CD Workflows
```

---

## 8. Antigravity Subagent Registry & Parallel Orchestration (`.agents/agents/`)

In Antigravity, the main session operates as **`HarnessOrchestrator`**: direct freeform coding or self-reviewing in the main session is prohibited. Dispatch specialized `.agents/agents/harness-*.md` subagents via `invoke_subagent` (parallelizing independent waves in one turn), inspect existing runs via `manage_subagents`, and resume via `send_message`:

| Subagent Name | Model | Policy | Tools | Role & Primary Output |
| :--- | :---: | :---: | :--- | :--- |
| `harness-onboarding` | `flash` | `off` | `view_file, grep_search` | Wave 1: Read-only repository & baseline diagnostics |
| `harness-planner` | `pro` | `off` | `view_file, replace_file_content, grep_search` | Wave 2: Architecture plan (`plan.md`, <= 5 checkpoints) & `sprint-active.md` |
| `harness-developer` | `pro` | `sandbox` | `view_file, replace_file_content, grep_search, run_command` | Wave 3: Full-stack implementation, targeted tests, `developer.md` |
| `harness-reviewer` | `flash` | `off` | `view_file, replace_file_content, grep_search` | Wave 4: Single-pass 11-dimension audit (`review.md`, >= 90 required) |
| `harness-verifier` | `flash` | `sandbox` | `view_file, replace_file_content, grep_search, run_command` | Wave 4: Static/test/build/health gate execution (`verification.md`) |
| `harness-documentation` | `flash` | `off` | `view_file, replace_file_content, grep_search` | Wave 5: OpenAPI, Qdrant & progress docs sync (`documentation.md`) |
| `harness-evaluator` | `flash` | `sandbox` | `view_file, replace_file_content, grep_search, run_command` | Wave 5: RAGAS, TTFT & security regression scoring (`benchmark.md`) |
| `harness-deployment` | `pro` | `sandbox` | `view_file, replace_file_content, grep_search, run_command` | Wave 6: Alembic migration, canary rollout, 3x health probe, rollback |
| `harness-recorder` | `flash` | `sandbox` | `view_file, replace_file_content, grep_search, run_command` | Wave 6: 6 Runtime Auditor gates & `scripts/harness_seal.py` closeout |

- **6-Wave DAG**: Wave 1 (`harness-onboarding` -> `issue.md`) -> Wave 2 (`harness-planner` -> `plan.md`) -> Wave 3 (`harness-developer` single or parallel disjoint tracks -> `developer.md`) -> Wave 4 (`harness-reviewer` || `harness-verifier`) -> Wave 5 (`harness-documentation` || optional `harness-evaluator`) -> Wave 6 (optional `harness-deployment` -> `harness-recorder`).
- **Retry & Escalation Caps**: Developer local self-fix max **3**; Reviewer->Developer fix loop max **2**; `FATAL_SECURITY_BLOCK` / `FATAL_SECURITY_FAIL` halts immediately for human escalation.

---

## 9. Strict Engineering, Security & UI Invariants

1. **Mandatory Evidence Sandbox**: Never edit `backend/` or `frontend/` before `.harness/runs/<ID>/issue.md` and `plan.md` exist. Every run produces all 9 core evidence files under `.harness/runs/<ID>/` (`issue.md`, `plan.md`, `developer.md`, `review.md`, `documentation.md`, `verification.md`, `summary.json`, `timeline.md`, `runtime.log`, plus `benchmark.md` / `deployment.md` when applicable).
2. **Python Virtual Environment**: ALWAYS run Python tooling via `backend/.venv/Scripts/python.exe` with `PYTHONUTF8=1`. NEVER invoke system global `python` or `pytest`.
3. **No Frontend Hardcoded Business Parameters**: Never hardcode fake product names, quantities, or prices in frontend components. Backend logic must extract tool/approval slots from real user input + multi-turn context and ask natural-language clarifying questions when required slots are missing.
4. **Low-Latency Non-Thinking Internal LLM & Zero Leak**: Intent routing and query rewriting LLM calls MUST use `thinking=False`, `streaming=False`, strict timeout control, deterministic offline fallback (`local_fallback`), and stream isolation (`callbacks=[]`, internal node/tag filtering). Never leak routing tags, sub-queries, JSON payloads, or debug jargon into the employee UI.
5. **Strict RBAC & Secret Isolation**: Never expose admin LLM settings, node configs, document ingestion, or telemetry controls in the `employee` view. Never return plaintext API Keys or Secret Keys from any endpoint.
6. **Zero System Emoji & Dual-Theme WCAG**: Never place system emojis in frontend UI or backend user-facing labels (`lucide-vue-next` and `@hugeicons/vue` only). Preserve warm-white Light mode (contrast >= 7:1) and obsidian Dark mode (contrast >= 4.5:1).
7. **Scope Lock**: Do not implement excluded/deferred items unless explicitly re-authorized: `[EXCLUDED]` 4-level security clearance UI switcher; `[DEFERRED]` `/workflows` visual editor and `/eval` / `/feedback` DPO workbench.

---

## 10. Context Anti-Bloat, Read-Deny & Output Noise-Reduction Rules

1. **Prohibited Default Reads (禁止读取清单，对齐 `.claude/settings.json`)**:
   - **`.harness/runs/**`**: Prohibited from unconditional/bulk reading across historical run folders (only read specific active `<ID>` artifacts required by the current Harness stage).
   - **`docs/sample_kb/**`**: Prohibited from reading sample knowledge-base corpus files during normal coding/review/planning turns.
   - **`docs/archive/**`**: Prohibited from reading archived historical documents.
2. **Sliced File Reading & Pre-Extracted Scope/Diff**:
   - **Prohibit full-file reads on files `> 200` lines** or bulky artifacts (`docs/generated/openapi-spec.json`, `Summary.md`, `docs/PROJECT_PROGRESS.md`, `docs/FRONTEND_PROGRESS.md`, large `.py`/`.vue` modules).
   - ALWAYS locate symbols/line numbers with `grep_search` first, then call `view_file` (or `read_file`) with explicit line ranges (`100-200` lines per slice).
   - Before Wave 4, `HarnessOrchestrator` MUST pre-generate `.harness/runs/<ID>/scope.md` and `.harness/runs/<ID>/diff.patch` via `PYTHONUTF8=1 backend/.venv/Scripts/python.exe scripts/harness_prepare_review.py <ID>`. Subagent briefs point to these paths instead of pasting huge file lists or unscoped diffs.
3. **Single-Pass Multi-Dimension Review & Checkpoint-Resume**:
   - NEVER split the 11-dimension review across multiple subagents; Wave 4 MUST invoke **strictly 1 `harness-reviewer`** (tool-call cap `<= 40`, persisting `.harness/runs/<ID>/review-checkpoint.json` every 2–3 dimensions) in parallel with **1 `harness-verifier`** (`verify-checkpoint.json` keyed by `code_hash`).
   - Before retrying or re-spawning after interruption/429, call `manage_subagents` (`list`) first and resume existing subagents via `send_message` instead of spawning duplicates.
4. **Hard-Capped Command Output Noise Reduction (对齐 `PreToolUse` Hooks)**:
   - Enforce **`stdout <= 50` lines** (`<= 2k` tokens) on all shell/command invocations.
   - `harness-developer` runs **targeted tests ONLY**; full-repo `pytest` runs ONCE during Wave 4 verification.
   - Wrap noisy commands (`pytest`, `ruff`, `mypy`, `npm run build`) via `PYTHONUTF8=1 backend/.venv/Scripts/python.exe scripts/harness_run.py --name <gate> -- <cmd>` (full logs archived to `.harness/logs/`).
   - For `pytest`, force `-q --tb=short --no-header` (or `--tb=line --no-header` + `--deselect` for documented baseline failures). Pipe long logs through `Select-String` / `Select-Object -Last 50` (PowerShell) or `grep` / `tail -n 50` (Bash). Never paste raw logs into reports.
5. **Compact Edits, Mechanical Closeout & Cache Hygiene**:
   - Keep edits concise and targeted; use `PYTHONUTF8=1 backend/.venv/Scripts/python.exe scripts/harness_seal.py <ID>` for Stage 10 closeout.
   - Never write dynamic timestamps, Git hashes, or run counters into `AGENTS.md` so prompt prefix caching stays warm.
