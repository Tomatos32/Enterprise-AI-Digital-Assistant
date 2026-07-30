# Enterprise AI Harness - Health Check & Probe Specification
> 企业级 AI 数字员工平台——健康检查探针与就绪规范说明书 (V1.0)

---

## 1. 探针设计原则 (Probe Design)

系统的健康检查分为 **Liveness Probe（存活探针）** 与 **Readiness Probe（就绪探针）**：
- **Liveness Probe**：验证 FastAPI 主事件循环（Event Loop）是否正常运行，未陷入无限死循环或内存爆破。
- **Readiness Probe**：深度验证业务依赖服务（MySQL、Redis、Qdrant、vLLM 推理端）的网络连通性与读写可用性。

---

## 2. API Endpoint 定义与 Payload

### 接口规范：`GET /api/v1/health`

#### 2.1 健康正常响应范例 (HTTP 200 OK)

```json
{
  "status": "HEALTHY",
  "timestamp": "2026-07-22T02:20:45Z",
  "version": "1.0.4",
  "components": {
    "mysql": {
      "status": "UP",
      "latency_ms": 3.2
    },
    "redis": {
      "status": "UP",
      "latency_ms": 1.1
    },
    "qdrant": {
      "status": "UP",
      "latency_ms": 8.5
    },
    "vllm_inference": {
      "status": "UP",
      "latency_ms": 12.0
    }
  }
}
```

#### 2.2 服务失能响应范例 (HTTP 503 Service Unavailable)

```json
{
  "status": "UNHEALTHY",
  "timestamp": "2026-07-22T02:20:45Z",
  "version": "1.0.4",
  "components": {
    "mysql": {
      "status": "UP",
      "latency_ms": 3.2
    },
    "qdrant": {
      "status": "DOWN",
      "error": "Connection refused to qdrant:6333"
    }
  }
}
```

---

## 3. Kubernetes / Docker Compose 探针配置范例

```yaml
# K8s Container Probe Configuration
readinessProbe:
  httpGet:
    path: /api/v1/health
    port: 8000
  initialDelaySeconds: 15
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 3

livenessProbe:
  httpGet:
    path: /api/v1/health
    port: 8000
  initialDelaySeconds: 20
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
```
