# Enterprise AI Digital Assistant - Deployment & Operations Guide
> 企业级 AI 数字员工平台部署与运维指南 (V1.0)

---

## 1. 部署架构说明

企业数字员工平台支持**混合云部署**及**全私有化本地部署**。
在全私有化部署环境下，核心大模型计算依托于本地私有 GPU 服务器，通过 **vLLM** 驱动推理；业务层通过 **Docker Compose** 或 **Kubernetes (K8s)** 进行微服务容器化编排，以保障数据的绝对隐私安全及低延迟内网交互。

---

## 2. 基于 Docker Compose 的单机快速部署

适用于开发、测试环境或中小型企业私有化部署场景。通过单台搭载 NVIDIA GPU（如单张 A800/H20 或 RTX 4090）的服务器即可拉起整套服务。

### 2.1 项目 `docker-compose.yml` 完整配置

```yaml
version: '3.8'

services:
  # 1. 业务数据库 (MySQL)
  mysql:
    image: mysql:8.0.32
    container_name: ea-mysql
    restart: always
    environment:
      MYSQL_DATABASE: enterprise_ai
      MYSQL_ROOT_PASSWORD: RootSecurePassword2026
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "root", "-pRootSecurePassword2026"]
      interval: 10s
      timeout: 5s
      retries: 5

  # 2. 高并发缓存与队列 (Redis)
  redis:
    image: redis:7.0-alpine
    container_name: ea-redis
    restart: always
    command: redis-server --appendonly yes --requirepass RedisSecurePassword2026
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "RedisSecurePassword2026", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # 3. 向量数据库 (Qdrant)
  qdrant:
    image: qdrant/qdrant:v1.7.4
    container_name: ea-qdrant
    restart: always
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 10s
      timeout: 5s
      retries: 5

  # 4. 对象存储 (MinIO - S3 兼容)
  minio:
    image: minio/minio:RELEASE.2023-10-16T04-13-43Z
    container_name: ea-minio
    restart: always
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: minio_admin
      MINIO_ROOT_PASSWORD: MinioSecurePassword2026
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 10s
      timeout: 5s
      retries: 5

  # 5. FastAPI 后端网关与 API 服务
  gateway:
    image: enterprise-ai-gateway:latest
    build:
      context: ../backend
      dockerfile: Dockerfile
    container_name: ea-gateway
    restart: always
    depends_on:
      mysql:
        condition: service_healthy
      redis:
        condition: service_healthy
      qdrant:
        condition: service_healthy
      minio:
        condition: service_healthy
    environment:
      - DATABASE_URL=mysql+pymysql://root:RootSecurePassword2026@mysql:3306/enterprise_ai?charset=utf8mb4
      - REDIS_URL=redis://:RedisSecurePassword2026@redis:6379/0
      - QDRANT_HOST=qdrant
      - QDRANT_PORT=6333
      - S3_ENDPOINT=http://minio:9000
      - S3_ACCESS_KEY=minio_admin
      - S3_SECRET_KEY=MinioSecurePassword2026
      - S3_BUCKET=knowledge-docs
      - LLM_API_BASE=http://vllm-inference:8000/v1
      - LLM_API_KEY=vllm_local_token_secure_2026
      - EMBEDDING_MODEL_PATH=BGE-M3
    ports:
      - "8000:8000"

  # 6. Celery 异步任务执行器 (处理文档 OCR/切片向量化)
  celery_worker:
    image: enterprise-ai-gateway:latest
    container_name: ea-celery-worker
    restart: always
    depends_on:
      redis:
        condition: service_healthy
    command: celery -A tasks.celery_app worker --loglevel=info -c 4
    environment:
      - DATABASE_URL=mysql+pymysql://root:RootSecurePassword2026@mysql:3306/enterprise_ai?charset=utf8mb4
      - REDIS_URL=redis://:RedisSecurePassword2026@redis:6379/0
      - QDRANT_HOST=qdrant
      - QDRANT_PORT=6333
      - S3_ENDPOINT=http://minio:9000
      - S3_ACCESS_KEY=minio_admin
      - S3_SECRET_KEY=MinioSecurePassword2026
      - S3_BUCKET=knowledge-docs
      - EMBEDDING_MODEL_PATH=BGE-M3

volumes:
  mysql_data:
  redis_data:
  qdrant_data:
  minio_data:
```

---

## 3. 基于 Kubernetes (K8s) 的分布式企业部署

在大型高并发场景下，需通过 Kubernetes 将系统进行横向伸缩与高可用部署。

### 3.1 Gateway 部署描述文件 (`ea-gateway-deployment.yaml`)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ea-gateway
  namespace: enterprise-ai
  labels:
    app: ea-gateway
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ea-gateway
  template:
    metadata:
      labels:
        app: ea-gateway
    spec:
      containers:
      - name: gateway
        image: harbor.internal.corp/enterprise-ai/gateway:v1.0.0
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 8000
        resources:
          limits:
            cpu: "2"
            memory: 4Gi
          requests:
            cpu: "1"
            memory: 2Gi
        envFrom:
        - configMapRef:
            name: ea-config
        - secretRef:
            name: ea-secrets
        readinessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 15
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 20
          periodSeconds: 15
---
apiVersion: v1
kind: Service
metadata:
  name: ea-gateway-svc
  namespace: enterprise-ai
spec:
  selector:
    app: ea-gateway
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: ClusterIP
```

### 3.2 Ingress 网关配置（开启 WebSocket 支持）

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ea-ingress
  namespace: enterprise-ai
  annotations:
    kubernetes.io/ingress.class: "nginx"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "3600"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "3600"
    nginx.ingress.kubernetes.io/websocket-services: "ea-gateway-svc"
spec:
  rules:
  - host: ai-agent.internal.corp
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: ea-gateway-svc
            port:
              number: 80
```

---

## 4. 本地 LLM 推理引擎 (vLLM) 部署与调优

对于私有化智能体系统，大模型推理速度是核心瓶颈。我们采用 **vLLM** 部署 `Qwen2.5-72B-Instruct` 级企业主力大模型。

### 4.1 硬件算力评估要求
`Qwen2.5-72B-Instruct` 在 FP16 精度下，模型权重大小约为 144GB。
- **推荐硬件**：2 张 NVIDIA H20 (96GB HBM) 或 2 张 A800 (80GB SXM)，通过 NVLink 互联。
- **量化部署方案**：若使用 INT4 / INT8 GPTQ 量化版模型，可运行在单张 80GB（如 A100/A800 80G）显卡上。

### 4.2 vLLM 启动指令与参数调优

在私有 GPU 服务器上，通过以下 Shell 指令启动推理服务：

```bash
python3 -m vllm.entrypoints.openai.api_server \
    --model /model_weights/Qwen2.5-72B-Instruct-AWQ \
    --port 8000 \
    --host 0.0.0.0 \
    --tensor-parallel-size 2 \
    --trust-remote-code \
    --enable-prefix-caching \
    --max-model-len 32768 \
    --gpu-memory-utilization 0.90 \
    --max-num-seqs 256 \
    --api-key vllm_local_token_secure_2026
```

#### 核心调优参数深度解析：
1. **`--tensor-parallel-size 2` (张量并行度)**：
   设置 TP=2。将模型的计算算子横向切分到两张 GPU 上并行计算，大幅度压缩单次 Token 推理时间，解决单卡显存不足的问题。
2. **`--enable-prefix-caching` (前缀缓存机制 - Prompt Cache)**：
   **核心开关**。开启后，vLLM 会对系统 Prompt 和 RAG 匹配出的背景上下文生成对应的 KV Cache Block 并驻留显存。后续若其他请求携带相同的上下文前缀，Prefill 计算耗时接近 **0**，首 Token 耗时（TTFT）降低 80% 以上，并能成倍提升多并发下的吞吐率。
3. **`--gpu-memory-utilization 0.90` (显存占用上限)**：
   允许 vLLM 引擎预分配 90% 的显卡物理显存，预留 10% 显存用于处理并发请求带来的动态 KV Cache 膨胀，防止发生 Cuda Out-Of-Memory (OOM)。
4. **`--max-model-len 32768` (最大上下文窗口)**：
   将最大上下文长度截断为 32k，防止用户灌入极端长文本导致显存爆裂。

---

## 5. 系统性能监控与日志排查

### 5.1 Prometheus 指标收集
FastAPI 通过集成的 `prometheus_client` 吐出模型吞吐及网络指标：
- `http_requests_total`: API 请求总量。
- `llm_token_generation_speed`: 每秒生成的 Token 数量指标。
- `qdrant_search_latency_seconds`: 向量库检索延迟。

### 5.2 日志排查最佳实践
当发生大模型回答故障时，应遵循以下链路进行定位排查：

```text
                                 User reports bug
                                        │
                                        ▼
                                 Check Ingress Logs
                            (Network / WebSockets break?)
                                        │
                                        ▼
                                Check Gateway Logs
                           (FastAPI routing, JWT fail?)
                                        │
                                        ▼
                               Check LangGraph State
                             (thread_id, Checkpoint)
                                        │
                                        ▼
                             ┌──────────┴──────────┐
                             ▼                     ▼
                       Check RAG Logs        Check vLLM Logs
                     (Qdrant, Embedding)    (GPU OOM, Timeout)
```

1. **第一防线 (Ingress & WebSockets)**：
   查看 Nginx 容器日志，确认 WebSocket 是否因为未配置 Proxy Timeout 而发生中途超时自动断连（通常为 60 秒闲置）。
2. **第二防线 (Gateway & FastAPI)**：
   使用命令 `docker logs -f ea-gateway --tail 100` 查看 API 主日志，检查有无 Python 语法报错或 DB 连接失效错误。
3. **第三防线 (LangGraph 状态追踪)**：
   提取报错会话的 `thread_id`，在 MySQL `chat_messages` 和 `approvals` 中检索执行链路，判断状态机是否正确触发了挂起与恢复。
4. **第四防线 (vLLM 推理端)**：
   检查 GPU 服务器的推理日志，确认是否发生了显存碎片化导致的 GPU OOM。使用命令 `nvidia-smi` 查看两张显卡的负载是否均衡。
