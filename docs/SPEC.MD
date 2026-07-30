# Enterprise AI Digital Assistant
> 基于 LangGraph + RAG + 企业工作流的企业级 AI 数字员工平台

---

# 1. 项目简介

## 1.1 项目背景

随着企业数字化转型的推进，大语言模型（LLM）已逐渐成为企业知识管理、业务自动化和智能决策的重要基础设施。然而，大多数企业在 AI 落地过程中仍然面临以下问题：

- 企业知识分散，无法统一管理
- LLM 容易产生幻觉（Hallucination）
- AI 无法直接调用企业系统
- 长流程任务无法自动执行
- Token 成本高，缺乏统一监控
- AI 无法参与企业审批流

本项目旨在构建一个能够真正服务企业业务的 **Enterprise AI Digital Assistant（企业数字员工平台）**，实现 AI + 企业知识库 + 企业业务流程的一体化解决方案。

---

# 2. 项目目标

本项目目标如下：

- 构建企业级 RAG 知识库
- 构建 LangGraph Agent Workflow
- 接入企业数据库与业务系统
- 支持 Human-in-the-loop 审批
- 支持异步任务处理
- 支持 WebSocket 流式输出
- 支持 Prompt Cache 与 Token 成本统计
- 支持本地 LLM（vLLM）部署
- 支持企业 SOP 自动化执行

---

# 3. 技术架构

```text
                        Web UI
                           │
                    FastAPI Gateway
                           │
           ┌───────────────┴───────────────┐
           │                               │
       REST API                      WebSocket
           │
           ▼
                LangGraph Agent
                       │
 ┌─────────────┬───────────────┬──────────────┐
 │             │               │              │
Intent      Planner         Memory        Workflow
Router                                      Engine
 │                                          │
 ▼                                          ▼
Tool Call                              Human Approval
 │
 ├──────────────┬──────────────┐
 │              │              │
MySQL        Redis         Qdrant
 │                             │
业务数据                    企业知识库
```

---

# 4. 技术栈

| 模块 | 技术方案 |
|------|----------|
| 后端 | FastAPI |
| Agent | LangGraph |
| Agent Framework | LangChain |
| LLM | Qwen3 / DeepSeek / GPT |
| 本地推理 | vLLM |
| Embedding | BGE-M3 |
| Reranker | BGE-Reranker |
| 向量数据库 | Qdrant |
| 数据库 | MySQL |
| 缓存 | Redis |
| 消息队列 | Celery |
| 实时通信 | WebSocket |
| 部署 | Docker Compose |
| 工作流 | Dify / n8n（可选） |

---

# 5. 系统功能

## 5.1 企业知识库（RAG）

支持：

- PDF
- Word
- Excel
- Markdown
- 图片 OCR

文档处理流程：

```
上传文档
    │
    ▼
Document Parser
    │
    ▼
Chunk
    │
    ▼
Embedding
    │
    ▼
Qdrant
```

支持：

- Metadata
- Table Parsing
- OCR
- 增量更新

---

## 5.2 Hybrid Retrieval

采用混合检索方案：

```
Query
 │
 ├── BM25
 │
 └── Dense Retrieval
        │
        ▼
    Merge Results
        │
        ▼
     Reranker
        │
        ▼
      Top-K
```

特点：

- Keyword Search
- Vector Search
- Metadata Filter
- Query Rewrite
- Multi Query

---

## 5.3 LangGraph Agent

工作流：

```
START
 │
 ▼
Intent Router
 │
 ├── Knowledge
 ├── Tool
 ├── Workflow
 └── Approval
 │
 ▼
Generate Response
 │
 ▼
END
```

支持：

- State Machine
- Retry
- Interrupt
- Resume
- Loop Protection

---

## 5.4 企业工具调用

采用 Function Calling + JSON Schema。

工具包括：

- 查询员工信息
- 查询库存
- 查询采购记录
- 创建工单
- 创建采购申请
- 企业微信通知
- 邮件通知

---

## 5.5 Human-in-the-loop

审批流：

```
用户提交采购
      │
      ▼
Agent生成申请
      │
      ▼
等待主管审批
      │
      ▼
审批通过
      │
      ▼
继续执行
```

---

## 5.6 企业数据库

### MySQL

保存：

- 用户
- 工单
- 审批
- 库存
- ERP 数据

### Qdrant

保存：

- 企业知识 Embedding
- Metadata

---

## 5.7 WebSocket Streaming

实时返回：

```
正在查询知识库...

↓

正在调用ERP...

↓

正在生成答案...

↓

完成
```

---

## 5.8 异步任务

Celery + Redis：

用于：

- OCR
- PDF解析
- Embedding
- Index构建
- 大文件导入

---

## 5.9 Prompt Cache

流程：

```
Prompt
 │
 ▼
Hash
 │
 ▼
Redis
 │
 ▼
直接返回
```

降低 Token 消耗。

---

## 5.10 Fallback

模型降级策略：

```
GPT

↓

Qwen

↓

DeepSeek

↓

Rule Engine
```

保证系统稳定运行。

---

# 6. 数据库设计

## User

| 字段 | 类型 |
|------|------|
| id | bigint |
| name | varchar |
| department | varchar |
| role | varchar |

---

## Ticket

| 字段 | 类型 |
|------|------|
| ticket_id | bigint |
| title | varchar |
| status | varchar |
| assignee | varchar |

---

## Approval

| 字段 | 类型 |
|------|------|
| approval_id | bigint |
| ticket_id | bigint |
| status | varchar |

---

## Knowledge

| 字段 | 类型 |
|------|------|
| doc_id | bigint |
| title | varchar |
| category | varchar |

---

# 7. Agent 状态设计

```
Idle

↓

Understand

↓

Retrieve

↓

Reason

↓

Tool

↓

Approval

↓

Generate

↓

Finish
```

---

# 8. Tool 设计

统一采用 JSON Schema：

```
create_ticket()

query_employee()

query_inventory()

query_policy()

create_purchase()

send_email()
```

---

# 9. 性能目标

| 指标 | 目标 |
|------|------|
| 首 Token | < 2 s |
| Retrieval | < 300 ms |
| RAG 响应 | < 5 s |
| WebSocket | 实时 |
| 并发 | ≥100 |
| Cache 命中率 | >70% |

---

# 10. 安全设计

支持：

- JWT 登录
- RBAC 权限控制
- Prompt Injection 防护
- SQL 参数化
- 敏感词检测

---

# 11. 项目亮点

- Hybrid Search（BM25 + Vector）
- LangGraph State Machine
- Human-in-the-loop
- Function Calling
- WebSocket Streaming
- Celery 异步任务
- Prompt Cache
- Token Cost Monitor
- Local LLM（vLLM）
- 企业 SOP 工作流

---

# 12. 开发 Roadmap

## Sprint 1：基础框架

- Fork LangGraph 官方 Template
- FastAPI
- Docker Compose
- MySQL
- Redis
- Qdrant

---

## Sprint 2：知识库

- PDF Parser
- OCR
- Chunk
- Embedding
- Qdrant

---

## Sprint 3：Hybrid Retrieval

实现：

- BM25
- Dense Retrieval
- Reranker

---

## Sprint 4：LangGraph

完成：

- Router
- Retrieve Node
- Tool Node
- Memory

---

## Sprint 5：Function Calling

开发：

- Tool Registry
- JSON Schema
- Tool Executor

---

## Sprint 6：企业系统 Mock

模拟：

- ERP API
- OA API
- HR API

---

## Sprint 7：审批流

实现：

- Interrupt
- Resume
- Approval

---

## Sprint 8：WebSocket

实现：

- Streaming Response
- Vue Chat UI

---

## Sprint 9：异步任务

Celery：

- OCR
- Index
- Embedding

---

## Sprint 10：AI Infra

完成：

- vLLM
- Prompt Cache
- Token Monitor
- Fallback

---

## Sprint 11：RAG Evaluation

引入：

- RAGAS
- Faithfulness
- Recall
- Precision

生成自动评估报告。

---

## Sprint 12：数字化转型 Demo

接入：

- Dify
- n8n
- Webhook
- 企业微信（Mock）

最终形成完整企业工作流：

```
用户提问
      │
      ▼
Intent Router
      │
      ▼
知识查询 / Tool 调用
      │
      ▼
审批节点（Human-in-the-loop）
      │
      ▼
执行企业流程
      │
      ▼
通知用户
```

---

# 13. 项目目录

```text
enterprise-ai-agent/
│
├── backend/
│   ├── api/
│   ├── graph/
│   ├── rag/
│   ├── workflow/
│   ├── tools/
│   ├── services/
│   ├── models/
│   ├── tasks/
│   └── config/
│
├── frontend/
│
├── docs/
│   ├── SPEC.md
│   ├── Architecture.md
│   ├── API.md
│   ├── Database.md
│   ├── Workflow.md
│   ├── Deployment.md
│   └── Interview.md
│
├── docker/
│
├── docker-compose.yml
│
└── README.md
```

---

# 14. 面试能力映射

| JD 能力要求 | 项目体现 |
|------------|----------|
| RAG 与企业知识库工程 | PDF/Office 解析、Hybrid Search、Reranker、RAGAS |
| Agent 状态机 | LangGraph、Router、Memory、Human-in-the-loop |
| 企业系统集成 | FastAPI Mock ERP/OA/HR、MySQL + Qdrant |
| 高并发设计 | Redis、Celery、WebSocket |
| AI 基础设施 | vLLM、Prompt Cache、Token Monitor、Fallback |
| 数字化转型 | Dify / n8n、Webhook、SOP 自动化 |