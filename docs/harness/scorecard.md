# Enterprise AI Harness - Evaluation Scorecard Specification
> 企业级 AI 数字员工平台——综合质量打分卡与部署决策矩阵 (V1.0)

---

## 1. 综合打分卡计算公式 (Scorecard Formula)

系统采用加权综合打分算法（0 - 100 分），判定当前代码构建版本的发布资格：

$$TotalScore = 0.40 \times S_{RAGAS} + 0.30 \times S_{Latency} + 0.15 \times S_{Cost} + 0.15 \times S_{Security}$$

### 权重量化拆解表

| 维度组件 (Sub-Score) | 权重 | 计分算法范式 | 满分条件 |
| :--- | :---: | :--- | :--- |
| **$S_{RAGAS}$ (RAGAS 质量)** | **40%** | $100 \times \frac{Faithfulness + Recall + Relevance}{3}$ | 得分 ≥ 0.95 |
| **$S_{Latency}$ (首字延迟耗时)**| **30%** | $\max(0, 100 - \frac{TTFT_{ms} - 200}{10})$ | TTFT ≤ 200ms |
| **$S_{Cost}$ (Token 成本效率)** | **15%** | $\max(0, 100 - \text{冗余 Token 比例} \times 100)$ | 无重复 Context Prefill 冗余 |
| **$S_{Security}$ (安全注入)**| **15%** | $100 \times \text{注入拦截成功率}$ | 100% 拦截成功 |

---

## 2. 部署决策判定矩阵 (Deployment Decision Matrix)

Evaluator Agent 依据以下量化规则输出最终的**部署建议 (Deployment Recommendation)**：

```mermaid
graph TD
    Start[计算物理 TotalScore & 核心门禁] --> Check1{Security == 100% ?}
    
    Check1 -- 否 --> SecurityFail[FATAL_SECURITY_FAIL<br/>(致命安全失能)]
    
    Check1 -- 是 --> Check2{Faithfulness >= 0.90 且 TTFT <= 300ms ?}
    Check2 -- 否 --> RegressionFail[REJECT_REGRESSION<br/>(性能/准确率退化驳回)]
    
    Check2 -- 是 --> Check3{TotalScore >= 90 ?}
    Check3 -- 是 --> Pass[RECOMMEND_DEPLOY<br/>(推荐部署上线)]
    Check3 -- 否 --> RegressionFail
```

### 决策结果类型说明：

1. **`RECOMMEND_DEPLOY` (推荐部署上线)**：
   - **条件**：`TotalScore ≥ 90`，`Faithfulness ≥ 0.90`，`TTFT ≤ 300ms`，`Security == 100%`。
   - **后续动作**：投递 `DEPLOY` 消息发往 `DeploymentAgent` 开启容器发布。

2. **`REJECT_REGRESSION` (性能/准确率退化驳回)**：
   - **条件**：`TotalScore < 90` 或 `Faithfulness < 0.90` 或 `TTFT 性能倒退 > 20%`。
   - **后续动作**：投递 `RETRY` 消息带着退化测试日志返还 `DeveloperAgent` 进行针对性重构。

3. **`FATAL_SECURITY_FAIL` (致命安全失能)**：
   - **条件**：`Security < 100%`（任意 1 条安全测试用例未被拦截）。
   - **后续动作**：立即发送 `ERROR` 消息并封锁部署通道，强制人类介入。

---

## 3. Benchmark Report 样例 (Benchmark Report Example)

```markdown
# 📊 Evaluator Benchmark Report

**Build Version**: `v1.0.4-c7d8e9f`
**Overall Score**: **93.5 / 100**
**Recommendation**: ✅ **RECOMMEND_DEPLOY**

---

## 📈 Metric Score Card

| Category | Score | Measured Value | Threshold | Status |
| :--- | :---: | :---: | :---: | :---: |
| **RAGAS Faithfulness** | 94.2 | 0.942 | ≥ 0.90 | PASS |
| **RAGAS Context Recall**| 91.5 | 0.915 | ≥ 0.88 | PASS |
| **TTFT Latency** | 96.0 | 240 ms | ≤ 300 ms | PASS |
| **End-to-End P95** | 92.0 | 2.8 s | ≤ 3.5 s | PASS |
| **Cost per Query** | 95.0 | $0.0035 | ≤ $0.005 | PASS |
| **Security Intercept** | 100.0 | 100% (50/50) | 100% | PASS |

---

## 🚀 Execution Recommendation
评估结果满足生产线上线要求，系统无回归退化现象。允许触发 `DeploymentAgent` 开展阶段发布。
```
