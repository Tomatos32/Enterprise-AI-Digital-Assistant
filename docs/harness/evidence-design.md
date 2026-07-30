# Enterprise AI Harness - Runtime Evidence Architecture Specification
> 企业级 AI 数字员工平台——.harness/runs/ 物理运行证据链设计说明书 (V1.0)

---

## 1. 证据链哲学 (Evidence Architecture Philosophy)

在传统的软件开发中，日志（Logs）通常只是无序、非结构化的文本流，仅用于事后排查 Bug。而在 Harness Engineering 体系中，**.harness/runs/ 目录下的所有文件并非普通日志，而是证明 AI Agent 自主开发合法性与工程质量的“物理运行证据链 (Runtime Evidence Chains)”**。

### 核心特性：
1. **防篡改只读性 (Immutability)**：每个阶段的证据文件由对应的 Agent 签名创建，并在节点交接时物理锁定变为 Read-Only，防止后置 Agent 篡改前期履历。
2. **完全可追溯性 (Traceability)**：审计人员或人类架构师可以通过单次运行证据包，100% 还原从原始需求、提示词思考、代码 Patch 到测试用例、静态审计的完整过程。
3. **隔离性 (Isolation)**：每个 Issue 均拥有独立的沙盒证据目录 `.harness/runs/Issue-XXXX/`。

---

## 2. 证据链文件结构与全生命周期表

每一个 Issue 启动时，系统自动在 `.harness/runs/` 下建立对应的独立文件夹 `Issue-XXXX/`，其中包含以下 9 大物理证据文件：

```text
.harness/runs/Issue-0001/
├── issue.md              # [Stage 0] 原始 Issue 需求与验收标准快照
├── plan.md               # [Stage 1] Planner 生成的架构拆解与任务计划
├── developer.md          # [Stage 2] Developer 提交的代码修改与自测报告
├── review.md             # [Stage 3] Reviewer 审计生成的 11 维评分卡与意见
├── documentation.md      # [Stage 4] Documentation 导出的 Schema 与向量更新日志
├── verification.md       # [Stage 5] Verifier 运行的静态门禁校验审计
├── benchmark.md          # [Stage 6] Evaluator 评估的 RAGAS 得分与 TTFT 耗时 (Dev Mode)
├── deployment.md         # [Stage 7] Deployment 运行的金丝雀部署与探针日志 (Dev Mode)
└── summary.json          # [Kernel] Harness Orchestrator 汇聚的全生命周期元数据
```

---

## 3. 证据文件逐一说明 (File Specifications)

### 3.1 `issue.md` (原始需求证据)
- **作用**：固化原始 Issue 输入、人类架构师指派的目标、优先级、受影响组件范围及原始验收条件。
- **创建时间**：Issue 被创建或拉取启动的时刻（Stage 0）。
- **创建 Agent**：`HarnessOrchestrator` / `BootstrapOrchestrator`。
- **更新时间**：创建时一次性写入，后续禁止任何修改。
- **锁定时间**：创建后**立即物理锁定（Read-Only）**。

---

### 3.2 `plan.md` (规划方案证据)
- **作用**：记录 Planner Agent 对 Issue 的技术解构、文件修改范围预测、原子 Checkpoints 清单及本地验证指令。
- **创建时间**：Planner Agent 启动规划阶段（Stage 1）。
- **创建 Agent**：`Planner Agent`。
- **更新时间**：草案生成期间增量写入。
- **锁定时间**：Planner 向 Developer 派发 `TASK` 消息前**物理锁定**。

---

### 3.3 `developer.md` (编码与自测证据)
- **作用**：记录 Developer Agent 修改的文件清单、物理 Git Diff 哈希、Alembic 迁移脚本名、`ruff`/`mypy`/`pytest` 控制台输出全量日志。
- **创建时间**：Developer Agent 启动编码阶段（Stage 2）。
- **创建 Agent**：`Developer Agent`。
- **更新时间**：在每次本地 `pytest` 自测循环时更新控制台日志。
- **锁定时间**：Developer 向 Reviewer 派发 `ARTIFACT` 消息前**物理锁定**。

---

### 3.4 `review.md` (代码审查证据)
- **作用**：记录 Reviewer Agent 的 11 维得分矩阵、综合 ReviewScore、扣分原因、行号级修复建议及 `APPROVED` / `REJECTED_WITH_CHANGES` 判定。
- **创建时间**：Reviewer Agent 启动代码审计阶段（Stage 3）。
- **创建 Agent**：`Reviewer Agent`。
- **更新时间**：审查完成时一次性写入。
- **锁定时间**：发出 `DECISION`（通过）或 `REVIEW`（驳回）消息前**物理锁定**。

---

### 3.5 `documentation.md` (知识与 Schema 证据)
- **作用**：记录 OpenAPI 规格导出日志、`docs/API.md` / `Database.md` 物理 Patch 位置、`CHANGELOG.md` 追加内容及 Qdrant 向量重构建 Chunk 数量与 Point ID。
- **创建时间**：Documentation Agent 启动维护阶段（Stage 4）。
- **创建 Agent**：`Documentation Agent`。
- **更新时间**：Schema 导出与向量 Upsert 完成时写入。
- **锁定时间**：发出 `TASK` 消息给 Verifier 前**物理锁定**。

---

### 3.6 `verification.md` (静态校验审计证据)
- **作用**：记录 Verifier Agent 对整个仓库实施的物理静态审计结果（检查前 5 个证据文件是否存在、Git Commit 时间轴顺规性、`pytest.log` 哈希无伪造、MD5 规则库无篡改）。
- **创建时间**：Verifier Agent 启动静态审计阶段（Stage 5）。
- **创建 Agent**：`Verifier Agent`。
- **更新时间**：静态审计运行结束时写入。
- **锁定时间**：发出 `BENCHMARK` 消息前**物理锁定**。

---

### 3.7 `benchmark.md` (性能与 RAGAS 评估证据 - Dev Mode)
- **作用**：记录 Evaluator Agent 运行 `benchmark/test-dataset.json` 的 RAGAS 三项指标得分（Faithfulness, Recall, Relevance）、TTFT 首字延迟、单次问答美元成本及安全注入测试结果。
- **创建时间**：Evaluator Agent 启动评估阶段（Stage 6）。
- **创建 Agent**：`Evaluator Agent`。
- **更新时间**：压测与 RAGAS 计算完成时写入。
- **锁定时间**：发出 `DEPLOY` 消息前**物理锁定**。

---

### 3.8 `deployment.md` (部署与探针证据 - Dev Mode)
- **作用**：记录 Docker 镜像 Tag (`enterprise-ai-gateway:v1.0.4`)、`alembic upgrade head` 物理输出、金丝雀灰度占比及 `/api/v1/health` 探针连续 3 次返回的 HTTP 响应体。
- **创建时间**：Deployment Agent 启动部署阶段（Stage 7）。
- **创建 Agent**：`Deployment Agent`。
- **更新时间**：金丝雀切流与冒烟用例通过时写入。
- **锁定时间**：发送任务闭环 `TASK(Closed)` 消息前**物理锁定**。

---

### 3.9 `summary.json` (生命周期控制总表)
- **作用**：记录单次运行的机器可读全量元数据，包括 Run ID、Issue ID、模式 (BOOTSTRAP / DEVELOPMENT)、整体耗时、Token 消耗总总开销、各阶段的时间戳与最终关单状态。
- **创建时间**：`HarnessOrchestrator` 收到 Issue 并初始化环境的时刻（Stage 0）。
- **创建 Agent**：`HarnessOrchestrator`。
- **更新时间**：在每一个 Agent 状态节点转移时实时 Patch 节点状态。
- **锁定时间**：Issue 达到 `Closed` 状态时做最后的元数据汇总并**物理锁定**。

---

## 4. Issue 生命周期结束后的物理目录树 (Completed Structure)

当 Issue-0001 完成所有阶段并关单后，其在 `.harness/runs/` 目录下的最终只读结构如下：

```text
.harness/
└── runs/
    ├── Issue-0001/                             # [Issue 独立证据包目录]
    │   ├── issue.md                            # [RO] 原始 Issue-0001 需求定义与验收条件
    │   ├── plan.md                             # [RO] Planner 生成的技术设计与 Checkpoints
    │   ├── developer.md                        # [RO] Developer 的 Git Diff 哈希与 pytest 日志
    │   ├── review.md                           # [RO] Reviewer 的 11 维得分与 Approved 判定
    │   ├── documentation.md                    # [RO] OpenAPI 导出 & Qdrant 向量更新日志
    │   ├── verification.md                     # [RO] Verifier 的 5 大静态门禁审计结果
    │   ├── benchmark.md                        # [RO] RAGAS 得分 (0.942) 与 TTFT 延迟 (240ms)
    │   ├── deployment.md                       # [RO] Docker 镜像 Tag 与 HTTP 200 健康探针
    │   └── summary.json                        # [RO] 机器可读全生命周期 JSON 控制元数据
    └── Issue-0002/                             # [后续 Issue 物理隔离文件夹...]
```
