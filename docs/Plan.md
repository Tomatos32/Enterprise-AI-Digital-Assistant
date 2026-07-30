# Enterprise AI Digital Assistant - Project Development Plan
> 企业级 AI 数字员工平台项目开发与里程碑计划书 (V1.0)

---

## 1. 项目里程碑规划 (Milestones)

本项目开发周期预计为 **12 周 (12 Sprints)**，每个 Sprint 周期为 1 周。整体开发进度严格遵循“底层数据库/服务 -> 算法与工作流引擎 -> 外部系统对接 -> 流式渲染与前端 -> 本地化部署及评估”的交付逻辑，以确保项目的系统性与敏捷度。

```mermaid
gantt
    title 企业级数字员工平台项目开发甘特图
    dateFormat  YYYY-MM-DD
    section 阶段一：基础与存储
    Sprint 1: 基础框架与中间件        :active, des1, 2026-07-27, 7d
    Sprint 2: 知识库解析与文档管道    :         des2, after des1, 7d
    Sprint 3: 混合检索与重排重排      :         des3, after des2, 7d
    section 阶段二：智能体大脑
    Sprint 4: LangGraph 状态机核心   :         des4, after des3, 7d
    Sprint 5: 工具注册与函数调用      :         des5, after des4, 7d
    Sprint 6: ERP/HR 企业系统 Mock     :         des6, after des5, 7d
    section 阶段三：人机协同与展示
    Sprint 7: 审批挂起与中断恢复      :         des7, after des6, 7d
    Sprint 8: WebSocket流与前端聊天UI  :         des8, after des7, 7d
    Sprint 9: Celery 异步长任务处理   :         des9, after des8, 7d
    section 阶段四：底座调优与评估
    Sprint 10: 本地推理与 vLLM 调优   :         des10, after des9, 7d
    Sprint 11: RAGAS 自动评估体系     :         des11, after des10, 7d
    Sprint 12: 数字化 SOP 流程交付     :         des12, after des11, 7d
```

---

## 2. 迭代计划详细分解 (Sprint Breakdown)

### 2.1 阶段一：数据底座与检索体系 (Sprint 1 - 3)

#### Sprint 1：基础框架搭建与环境联调
- **核心目标**：构建工程脚手架，完成容器化基础中间件配置。
- **任务分解**：
  1. 搭建 FastAPI 基础架构，配置统一异常处理及响应拦截。
  2. 部署 MySQL 8.0 主从数据库、Redis 集群、Qdrant 向量库。
  3. 完成基于 JWT 密码校验的登录验证逻辑及 RBAC 中间件开发。
  4. 编写 Docker Compose 单机一键启动脚本。
- **交付物**：可启动的微服务基础骨架，通过健康检查（Health Check）。

#### Sprint 2：知识库解析与文档摄入管道 (Ingestion Pipeline)
- **核心目标**：实现复杂文档的清洗与向量化存盘。
- **任务分解**：
  1. 引入 Docling/Unstructured 模块，提取 PDF、DOCX 标题及段落层次结构。
  2. 集成 OCR 服务，解析文档中的表格和图片，并以 Markdown 结构化存储。
  3. 编写递归字符文本分块器（RecursiveCharacterTextSplitter），并添加部门、密级等元数据。
  4. 编写 Qdrant 写入逻辑，利用 BGE-M3 生成 Dense Embedding 并存盘。
- **交付物**：`POST /knowledge/upload` 文件异步处理服务。

#### Sprint 3：混合检索 (Hybrid Retrieval) 与 Reranker 引擎
- **核心目标**：提供兼具模糊语义和精确专有名词匹配的高精准检索。
- **任务分解**：
  1. 实现基于 Qdrant Dense Vector 的语义度量。
  2. 实现基于 ElasticSearch / Qdrant Sparse Vector 的 BM25 稀疏检索。
  3. 编写互惠排名融合 (RRF) 归一化融合逻辑。
  4. 引入 BGE-Reranker-Large 重排模型，完成前 Top-20 到 Top-5 的筛选。
- **交付物**：`POST /knowledge/search` 测试接口，首字检索延迟控制在 100ms 以内。

---

### 2.2 阶段二：LangGraph 智能体大脑构建 (Sprint 4 - 6)

#### Sprint 4：LangGraph 状态机核心框架
- **核心目标**：定义智能体 State 结构，构建控制节点拓扑。
- **任务分解**：
  1. 定义共享强类型 `AgentState` 字典。
  2. 编写 4 个核心节点（Intent Router、Retrieve、Tool Node、Response Generator）。
  3. 配置 Intent Router 使用 Few-Shot Prompt 对用户输入进行精细化语义分流。
  4. 接入 LangGraph PostgresCheckpointer，实现会话历史检查点持久化。
- **交付物**：跑通纯文本流下的意图识别路由与记忆闭环。

#### Sprint 5：Tool 注册器与 Function Calling 引擎
- **核心目标**：规范工具入参及执行结果回填。
- **任务分解**：
  1. 编写工具装饰器 `@tool`，使 Python 接口函数自动输出标准的 JSON Schema。
  2. 实现 `Tool Registry` 工具容器，管理已被授权调用的 ERP、OA 工具集。
  3. 编写 Tool Executor Node 动态解析 LLM 的工具调用参数并完成本地执行。
- **交付物**：Tool 节点能够根据 LLM 命令，输出正确的 JSON 请求参数。

#### Sprint 6：外部企业系统 (ERP/HR/OA) Mock 联调
- **核心目标**：构建模拟 ERP 接口数据，联调多路 Tool 调用。
- **任务分解**：
  1. 创建 Mock 数据库表结构（erp_employees, erp_inventory, erp_purchases）。
  2. 编写模拟 ERP 查询接口，支持按物料编码检索库存与价格。
  3. 模拟 HR 系统，支持查询人员归属部门。
  4. 联合调试：智能体通过调用员工查询和库存查询工具，回答用户的业务关联问题。
- **交付物**：具备完整业务场景数据的企业级 Mock 后端。

---

### 2.3 阶段三：人机协同与流式前端交付 (Sprint 7 - 9)

#### Sprint 7：Human-in-the-loop (人机协作审批流) 落地
- **核心目标**：实现高危工具的自动挂起拦截与审批复原。
- **任务分解**：
  1. 在 Tool Node 执行前嵌入安全控制规则。
  2. 针对采购超额任务调用 `interrupt()`，冻结当前的状态机执行链。
  3. 在 MySQL 的 approvals 表中插入 PENDING 记录，并模拟推送给主管。
  4. 编写 `POST /workflow/approvals/{id}/action` 接口，接收审批结果后 resume 状态机。
- **交付物**：工单审批中断与自动继续的集成测试用例。

#### Sprint 8：WebSocket 双工流式通道与前端 Vue 3 UI
- **核心目标**：实现高体验的实时消息通信与前端交互卡片。
- **任务分解**：
  1. 基于 FastAPI 实现长连接管理器（ConnectionManager），维持 WebSocket 长连接。
  2. 前端引入 Vue 3 + NuxtJS，基于 Tailwind CSS 构建现代化聊天窗口。
  3. 前端对接 WebSocket，能区分解析事件包（`node_intent`, `text_chunk`, `approval_interrupt`）。
  4. 前端实现审批单据点击同意后，实时观测右侧对话框 AI 状态卡片自动解冻。
- **交付物**：支持流式输出、具备卡片反馈的企业级 AI 会话大屏。

#### Sprint 9：Celery 异步长任务处理与多级缓存优化
- **核心目标**：提升系统并发与多用户请求下的性能体验。
- **任务分解**：
  1. 将 OCR 解析、PDF 分块及向量构建任务全量剥离到 Celery 后端执行。
  2. 配置 Redis 语义缓存（Semantic Cache），对高频问题进行相似度判别并秒级返回。
  3. 完成 Redis 对会话消息及审批缓存的快速读取。
- **交付物**：多并发环境压力测试报告，系统崩溃保护率达 100%。

---

### 2.4 阶段四：底座调优、质量评估与上线交付 (Sprint 10 - 12)

#### Sprint 10：私有化本地 LLM 推理 (vLLM) 调优
- **核心目标**：摆脱外网 API 依赖，实现企业级 GPU 算力极限提速。
- **任务分解**：
  1. 部署 vLLM 推理服务器，加载 Qwen-72B-Chat 或 DeepSeek-V3 AWQ 权重。
  2. 开启 `--enable-prefix-caching` (Prompt Cache) 选项。
  3. 配置 TP=2（张量并行），在双卡 A800/H20 上调优运行时显存参数。
  4. 开发 API Fallback（熔断与模型降级策略），在云端失效时切换至本地 vLLM。
- **交付物**：单次 RAG 推理 TTFT 降至 200ms 以内，并发承载路数 ≥100。

#### Sprint 11：RAGAS 自动评估体系与系统性压测
- **核心目标**：客观评定知识库问答的“幻觉率”和“召回率”。
- **任务分解**：
  1. 引入 RAGAS 工具包，定义评估指标（Faithfulness, Answer Relevance, Context Recall）。
  2. 编写评估脚本，自动化生成 200 个模拟 Query 对系统发起检索和生成。
  3. 通过本地小模型对输出质量打分，生成评估分析报告，迭代调整 Chunk 长度与重排阈值。
  4. 进行 48 小时持续性能压测，监控 CPU、GPU、内存泄露。
- **交付物**：RAGAS 评估报告，知识匹配准确率 > 92%。

#### Sprint 12：数字化 SOP 流程交付与生产级上线
- **核心目标**：对接企业常用工作流软件，生产环境正式上线。
- **任务分解**：
  1. 接入 n8n / Dify，实现复杂 Webhook 的流程回调绑定。
  2. 封包前端与后端 Docker 镜像，编写 Kubernetes (K8s) StatefulSets 及 Deployments 部署清单。
  3. 配置 Ingress 开启反向代理及安全头部防御（CSP, HSTS）。
  4. 面试能力映射文档校准与发布。
- **交付物**：线上运行的企业 AI 数字员工平台，全套企业级文档及上线报告。

---

## 3. 项目风险与应对策略

| 风险类别 | 风险描述 | 严重级别 | 应对策略 |
| :--- | :--- | :--- | :--- |
| **推理算力瓶颈** | 本地 72B 大模型在并发 > 50 时，推理延迟突增，首字延迟突破 3 秒。 | **高** | 1. 采用 GPTQ/AWQ 4-bit 量化，减少显存与内存带宽占用。<br>2. 强制开启 vLLM Prefix Caching，使连续会话复用 KV 缓存。<br>3. 设立限流机制，多出的请求进入 Redis 等待队列。 |
| **大模型幻觉** | 数字员工执行采购单时，由于幻觉读取了错误的物料编码，导致 ERP 采购错误。 | **致命** | 1. 关键写操作工具（如提交采购）的参数，必须经由 Qdrant 检索出的物料表做强类型校对正则匹配。<br>2. 设立 Human-in-the-loop 机制，凡是改变数据的操作一律拦截并由人工审批把关。 |
| **知识匹配率低** | 扫描版 PDF 文档由于双栏排版或图片扭曲，导致 OCR 解析错乱，检索不精准。 | **中** | 1. 使用 Docling 识别版面布局逻辑，去除噪声。<br>2. 提取表格后统一使用 Markdown Tabular 重新渲染并切片。<br>3. 检索时不仅靠 Dense Vector，还通过 BM25 对精准关键词做强加权。 |
| **API 服务抖动** | 依赖的云端 API（如 DeepSeek Cloud）遇到大面积断网或限流。 | **高** | 1. 编写 RobustLLMClient 降级路由链，一旦发生 API 网络报错，瞬间自动切换至本地部署的 vLLM Qwen 大模型。<br>2. 实在无法连接时，降级到基于预设模板规则的回复引擎，保证服务正常响应。 |
