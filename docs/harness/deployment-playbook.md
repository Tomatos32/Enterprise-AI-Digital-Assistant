# Enterprise AI Harness - Deployment Agent Execution Playbook
> 企业级 AI 数字员工平台——Deployment Agent 实战操作手册与范例 (V1.0)

---

## 1. 金丝雀灰度发布实战规程 (Canary SOP)

1. **解析 DEPLOY 入站消息**：提取入参镜像 Tag（如 `v1.0.4`）与评估分值。
2. **数据库迁移**：运行命令 `alembic upgrade head`，成功后输出日志。
3. **启动金丝雀容器**：部署 `ea-gateway-canary` 实例，接入 10% 网关流量。
4. **探针与冒烟**：对金丝雀容器进行 `/api/v1/health` 探针校验（间隔 5 秒，连续 3 次）。
5. **全量切流**：探针通过后，将流量放大至 100%，下线旧版本容器。
6. **任务闭环**：发送 `TASK(Status: Closed)` 消息给 Harness Orchestrator。

---

## 2. 真实演练范例 (Concrete Example)

### 2.1 接收到的 DEPLOY 入站消息体 (Inbound Message)

```json
{
  "message_id": "msg_dep_0901",
  "message_type": "DEPLOY",
  "sender": "EvaluatorAgent",
  "receiver": "DeploymentAgent",
  "status": "Running",
  "timestamp": "2026-07-22T02:20:00Z",
  "artifact": {
    "file_paths": ["docker-compose.yml"],
    "git_commit": "a1b2c3d4",
    "diff_hash": null
  },
  "payload": {
    "issue_id": "ISSUE-204",
    "recommendation": "RECOMMEND_DEPLOY",
    "total_score": 93.5,
    "target_image": "enterprise-ai-gateway:v1.0.4"
  }
}
```

---

### 2.2 Deployment Agent 执行的实战步骤日志

```text
[02:20:05] [Pre-Deploy] Verified Evaluator recommendation: RECOMMEND_DEPLOY (Score: 93.5).
[02:20:10] [Mid-Deploy] Executing Alembic DB Migration: `alembic upgrade head` ... SUCCESS.
[02:20:25] [Mid-Deploy] Building Docker Image: `enterprise-ai-gateway:v1.0.4` ... SUCCESS.
[02:20:30] [Mid-Deploy] Deploying Canary Instance (10% Traffic Ratio).
[02:20:45] [Post-Deploy] Polling Health Probe `/api/v1/health` ... 200 OK (3/3).
[02:20:50] [Post-Deploy] Executing Smoke Tests ... PASSED.
[02:21:00] [Release] Scaling Traffic to 100%. Old instances deprecated cleanly.
```

---

### 2.3 投递给 Harness Orchestrator 的任务闭环出站消息体 (Outbound TASK Message)

```json
{
  "message_id": "msg_task_0902",
  "message_type": "TASK",
  "sender": "DeploymentAgent",
  "receiver": "HarnessOrchestrator",
  "status": "Closed",
  "timestamp": "2026-07-22T02:21:10Z",
  "artifact": {
    "file_paths": [],
    "git_commit": "a1b2c3d4",
    "diff_hash": null
  },
  "payload": {
    "issue_id": "ISSUE-204",
    "deployment_status": "SUCCESS",
    "deployed_image": "enterprise-ai-gateway:v1.0.4",
    "health_check": "HTTP 200 OK",
    "thread_closed": true
  }
}
```
