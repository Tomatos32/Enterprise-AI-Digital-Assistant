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
  - `AGENTS.md`, `BOOTSTRAP.md`, `docs/harness/Runtime.md` & `docs/guidelines/*`: **HUMAN-ONLY / PROHIBITED FROM DIRECT AGENT EDITS**.
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

Before declaring any task complete, ALL of the following criteria MUST be met:

1. `ruff check backend/` returns ZERO errors.
2. `mypy backend/` passes strict static typing check.
3. `pytest backend/tests/` passes 100%.
4. Alembic Migration script exists in `backend/migrations/versions/` if ORM models changed.
5. Reviewer Agent outputs `APPROVED` status with Scorecard >= 90 (written to `review.md`).
6. Documentation Agent exports updated OpenAPI JSON & Qdrant vector index.
7. Active Task checkpoint marked `[x]` in `docs/plans/sprint-active.md`.
8. Harness Recorder flushes `.harness/runs/Issue-XXXX/` evidence package (`summary.json`, `timeline.md`, `runtime.log`).

---

## 7. Repository Structure Map

```text
enterprise-ai-agent/
├── AGENTS.md                             # [ROOT] Master Harness Navigation Map (This File)
├── BOOTSTRAP.md                          # [ROOT] Bootstrap Mode Operating Specification
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
