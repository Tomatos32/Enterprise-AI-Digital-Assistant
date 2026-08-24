# 全局 Mock 资产清单审计、记忆与生产环境真实数据对接替换规范
# Global Mock Inventory & Production Cutover Specification

> **文档性质**：生产割接基线与环境适配器记忆规范 (Production Cutover & Baseline Memory)  
> **所属阶段**：Sprint 14 专项任务 (Issue-0021)  
> **创建时间**：2026-08-24  
> **最后维护**：Harness Engineering V1.0  

---

## 1. 概述与生产割接愿景 (Executive Summary)

在系统的前序构建与验证阶段（Sprint 1 ~ 13），为了实现开发解耦、单测自包含与端到端闭环验证，系统在 **企业业务系统（HR/ERP/OA）、工作流消息通知（企业微信 Bot、n8n/Dify Webhook）、持久化数据源、知识库文件与 AI 大模型网关** 等 5 大模块中引入了模拟（Mock）实现与内存降级逻辑。

本文档作为**唯一权威的 Mock 资产清单与生产割接操作指南**，详尽记录了系统中每一个 Mock 节点的技术细节，并提供一键式环境变量切换契约，确保系统上线生产环境时能够“**零代码入侵、平滑无缝**”切换对接真实企业业务系统。

---

## 2. 全景 Mock 资产清单对照矩阵 (Master Mock Inventory Matrix)

```text
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 全系统 5 大核心维度 Mock 资产分布图                                     │
├──────────────────┬──────────────────┬──────────────────┬──────────────────┬────────────────────────────┤
│ 1. 企业业务系统  │ 2. 外部工作流    │ 3. 数据库与会话  │ 4. 知识库数据源  │ 5. AI 模型网关             │
│    (HR/ERP/OA)   │    (WeCom/Dify)  │    (SQLite/Pool) │    (Sample KB)   │    (Fallback/Cache)        │
├──────────────────┼──────────────────┼──────────────────┼──────────────────┼────────────────────────────┤
│ 员工/库存/工单   │ 内存消息队列     │ 内存静态连接池   │ 6 篇测试规章     │ 模拟备选响应               │
│ REST Mock API    │ Webhook 模拟路由 │ SQLite Fallback  │ Qdrant 本地集合  │ 本地规则 Fallback          │
└──────────────────┴──────────────────┴──────────────────┴──────────────────┴────────────────────────────┘
```

| 序号 | 模块名称 | 当前 Mock 机制与文件路径 | 生产真实系统对接技术方案 | 环境变量切换开关 (Config Flag) |
| :---: | :--- | :--- | :--- | :--- |
| **1** | **HR 员工信息查询** | `backend/api/v1/mock/hr.py`<br/>`backend/tools/impl/employee_tools.py` | 对接真实 **飞书人事 / 北森 / SAP SuccessFactors** OpenAPI | `USE_MOCK_SYSTEMS=False`<br/>`HR_BASE_URL=https://open.feishu.cn`<br/>`HR_APP_ID=...`<br/>`HR_APP_SECRET=...` |
| **2** | **ERP 物料库存查询** | `backend/api/v1/mock/erp.py`<br/>`backend/tools/impl/inventory_tools.py` | 对接真实 **SAP ERP / 用友 NC Cloud / 金蝶云星空** REST API | `USE_MOCK_SYSTEMS=False`<br/>`ERP_BASE_URL=https://erp.enterprise.com`<br/>`ERP_API_TOKEN=...` |
| **3** | **ERP 采购订单创建** | `backend/api/v1/mock/erp.py`<br/>`backend/tools/impl/purchase_tools.py` | 对接真实 **SAP MM 采购模块 / 甄云 SRM 采购系统** | `USE_MOCK_SYSTEMS=False`<br/>`ERP_PURCHASE_ENDPOINT=/api/v2/po/create` |
| **4** | **OA 故障工单流转** | `backend/api/v1/mock/oa.py`<br/>`backend/tools/impl/ticket_tools.py` | 对接真实 **Jira Service Desk / 泛微 e-cology / 飞书服务台** | `USE_MOCK_SYSTEMS=False`<br/>`OA_BASE_URL=https://oa.enterprise.com`<br/>`OA_APP_KEY=...` |
| **5** | **企业微信 Bot 通知** | `backend/api/v1/workflow.py`<br/>`MOCK_WECOM_MESSAGES` (内存列表) | 发送至真实 **企业微信群机器人 Webhook** 官方接口 | `WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY` |
| **6** | **n8n / Dify 事件联动** | `backend/api/v1/workflow.py`<br/>`POST /api/v1/webhook/event` | 投递至生产环境部署的 **n8n Workflow Webhook / Dify API** | `DIFY_API_BASE=https://api.dify.ai/v1`<br/>`DIFY_API_KEY=app-...`<br/>`N8N_WEBHOOK_URL=https://n8n.corp/webhook/...` |
| **7** | **E2E 演示数据库** | `backend/scripts/demo_e2e_closed_loop.py`<br/>`sqlite:///:memory:` (StaticPool) | 连接生产环境 **MySQL 8.0 主从复制高可用集群** | `MYSQL_SERVER=prod-mysql.internal`<br/>`MYSQL_PORT=3306`<br/>`MYSQL_USER=...` |
| **8** | **冷启动知识库文档** | `docs/sample_kb/*.md`<br/>`docs/sample_kb/*.pdf`, `*.xlsx` | 挂载企业 **SharePoint / Confluence / NAS 知识库源** | `KNOWLEDGE_BASE_SYNC_DIR=/mnt/enterprise_docs/`<br/>`QDRANT_HOST=prod-qdrant.internal` |
| **9** | **LLM 网关与降级** | `backend/core/llm_infra.py`<br/>`LLMGateway` (Fallback 假数据) | 对接真实 **Azure OpenAI / 阿里云通义千问 / 本地 vLLM 集群** | `OPENAI_API_KEY=sk-...`<br/>`OPENAI_API_BASE=https://...`<br/>`QWEN_API_KEY=sk-...` |

---

## 3. 各模块 Mock 细节与生产替换方案详解 (Module Deep-Dive)

### 3.1 维度一：企业业务系统 Mock (HR / ERP / OA)

#### 1. HR 员工查询 (`/api/v1/mock/hr/employee/{user_id}`)
- **当前 Mock 实现**：直接通过 SQLAlchemy 查询本地 MySQL `users` 表模拟员工信息。
- **涉及代码**：`backend/api/v1/mock/hr.py`，`backend/tools/impl/employee_tools.py`。
- **生产替换方案**：
  ```python
  # 生产适配器逻辑
  async def get_employee_info_prod(user_id: str) -> Dict[str, Any]:
      if settings.USE_MOCK_SYSTEMS:
          return await get_mock_employee(user_id)
      async with httpx.AsyncClient() as client:
          resp = await client.get(
              f"{settings.HR_BASE_URL}/open-apis/contact/v3/users/{user_id}",
              headers={"Authorization": f"Bearer {await get_tenant_access_token()}"}
          )
          return resp.json()
  ```

#### 2. ERP 库存与物料查询 (`/api/v1/mock/erp/inventory`)
- **当前 Mock 实现**：读取本地 `inventories` 表。
- **涉及代码**：`backend/api/v1/mock/erp.py`，`backend/tools/impl/inventory_tools.py`。
- **生产替换方案**：调用 SAP OData 接口 `GET /sap/opu/odata/sap/API_MATERIAL_STOCK_SRV/MaterialStock`。

#### 3. ERP 采购单据创建 (`/api/v1/mock/erp/purchase`)
- **当前 Mock 实现**：向本地 `purchases` 表插入记录，生成 `PO-XXXX`。
- **涉及代码**：`backend/api/v1/mock/erp.py`，`backend/tools/impl/purchase_tools.py`。
- **生产替换方案**：向 SAP SRM 提交 `POST /api/v1/purchase-orders`，携带采购物品、单价、审批单号与成本中心编号。

#### 4. OA 工单流转 (`/api/v1/mock/oa/ticket`)
- **当前 Mock 实现**：向本地 `tickets` 表插入记录，生成 `TCK-XXXX`。
- **涉及代码**：`backend/api/v1/mock/oa.py`，`backend/tools/impl/ticket_tools.py`。
- **生产替换方案**：调用 Jira REST API `POST /rest/api/3/issue` 或泛微 OA 工作流接口创建审批流单据。

---

### 3.2 维度二：工作流与 Webhook 模拟 (WeCom Bot & n8n / Dify)

#### 1. 企业微信 Bot Markdown 卡片推送
- **当前 Mock 实现**：
  - `backend/api/v1/workflow.py` 中的 `MOCK_WECOM_MESSAGES` 全局内存队列，用于单测与离线演示捕获推送。
- **生产替换方案**：
  - 在 `.env` 中配置真实的 `WECOM_WEBHOOK_URL`；
  - `dispatch_webhook_async` 检测到配置时，直接向企业微信发送 HTTP POST：
  ```python
  if settings.WECOM_WEBHOOK_URL:
      async with httpx.AsyncClient(timeout=5.0) as client:
          await client.post(settings.WECOM_WEBHOOK_URL, json=card_payload)
  ```

#### 2. n8n / Dify 工作流事件调度
- **当前 Mock 实现**：`EVENT_HISTORY` 内存列表记录事件；
- **生产替换方案**：配置 `N8N_WEBHOOK_URL` 与 `DIFY_API_BASE`，在状态机流转完成时同步推送结构化事件。

---

### 3.3 维度三：数据库与会话 Fallback (E2E 演示与生产 MySQL)

- **当前 Mock/演示实现**：
  - `backend/scripts/demo_e2e_closed_loop.py` 使用 `sqlite:///:memory:` 与 `StaticPool` 保证无需依赖本地真实数据库即可 100% 独立运行演示。
- **生产切换方案**：
  - 生产环境移除 `dependency_overrides`，直连 `settings.SQLALCHEMY_DATABASE_URI`（MySQL 8.0 主从连接池）。

---

### 3.4 维度四：冷启动知识库文档与向量库

- **当前 Mock 实现**：`docs/sample_kb/` 内置 6 篇模拟规章（`考勤休假管理办法`, `采购审批管理制度`, `报销规范`, `技术保密协议`, `IT资产运维手册`, `员工差旅标准`）。
- **生产切换方案**：
  - 部署 Celery Worker，配置 `async_parse_multimodal_file` 定时扫描企业知识库共享目录 `/mnt/enterprise_kb/` 并自动增量增量切片入库至 Qdrant。

---

### 3.5 维度五：AI 大模型网关与 Fallback 模拟

- **当前 Mock 实现**：`backend/core/llm_infra.py` 中当主模型未配置 API Key 时，返回预定义的规则兜底响应。
- **生产切换方案**：
  - 配置生产级 API Keys：`OPENAI_API_KEY`, `DEEPSEEK_API_KEY`, `QWEN_API_KEY`；
  - 启用 vLLM 本地内网高性能推理集群。

---

## 4. 生产环境一键切换配置规范 (`.env.production.example`)

在部署生产环境时，只需在根目录创建 `.env` 文件并填入以下真实生产配置：

```bash
# ==============================================================================
# Enterprise AI Digital Assistant - 生产环境一键切换配置模板 (.env)
# ==============================================================================

# 1. 核心运行环境
ENVIRONMENT=production
DEBUG=false
USE_MOCK_SYSTEMS=false

# 2. 真实 MySQL 生产数据库连接
MYSQL_SERVER=prod-mysql-cluster.internal
MYSQL_PORT=3306
MYSQL_USER=prod_ai_user
MYSQL_PASSWORD=SecurePassword2026!
MYSQL_DB=enterprise_ai_prod

# 3. 真实 Redis 生产集群
REDIS_HOST=prod-redis-sentinel.internal
REDIS_PORT=6379
REDIS_DB=0

# 4. 真实 Qdrant 向量数据库
QDRANT_HOST=prod-qdrant.internal
QDRANT_PORT=6333
QDRANT_COLLECTION=enterprise_knowledge_prod

# 5. 企业业务系统 OpenAPI 真实地址与认证
HR_BASE_URL=https://hr.enterprise.internal/api/v1
HR_API_TOKEN=hr_bearer_token_prod_xxx

ERP_BASE_URL=https://erp.enterprise.internal/api/v1
ERP_API_TOKEN=erp_bearer_token_prod_xxx

OA_BASE_URL=https://oa.enterprise.internal/api/v1
OA_API_TOKEN=oa_bearer_token_prod_xxx

# 6. 企业微信群机器人 Webhook (审批通知真实群广播)
WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=prod-wecom-bot-key-uuid

# 7. n8n / Dify 生产工作流平台
DIFY_API_BASE=https://dify.enterprise.internal/v1
DIFY_API_KEY=app-prod-secret-key-xxx
N8N_WEBHOOK_URL=https://n8n.enterprise.internal/webhook/prod-approval-listener

# 8. 大模型 API 生产凭证
OPENAI_API_KEY=sk-prod-openai-key-xxx
OPENAI_API_BASE=https://api.openai.com/v1
QWEN_API_KEY=sk-prod-qwen-key-xxx
DEEPSEEK_API_KEY=sk-prod-deepseek-key-xxx
```

---

## 5. 总结与后续 Issue 执行指引

- **资产核准**：全系统共计 **9 处 Mock 节点已全部审计并锁定归档**。
- **切换能力**：通过 `backend/core/config.py` 的集中配置，系统已完全具备“一键解除 Mock、切换生产真实系统”的能力。
- **后续行动**：完成 Issue-0021 关单后，系统将正式进入 `Issue-0022`（企业知识图谱与 Graph RAG 拓扑推理）。
