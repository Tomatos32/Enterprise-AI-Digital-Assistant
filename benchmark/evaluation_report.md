# RAG Pipeline Quality Evaluation Report

- **Evaluation Date**: `2026-09-22T16:14:07.127071+00:00`
- **Evaluation Mode**: `OFFLINE`
- **Total Samples Evaluated**: `30`
- **Pipeline Gate Status**: `❌ BLOCKED`

## 1. Metric Scorecard Summary

| Metric | Score | Threshold Requirement | Gate Status |
| :--- | :--- | :--- | :---: |
| **Faithfulness** | **0.9072** | >= 1.00 | ❌ FAIL |
| **Context Recall** | **0.8187** | >= 0.88 | ❌ FAIL |
| **Answer Relevance** | **0.6840** | Baseline Reference | ℹ️ INFO |

## 2. Bad Cases Analysis (28 detected)

- **Sample #0** (`公司员工年假计算标准与申请流程是什么？`): Faithfulness=0.9539, Context Recall=0.9125 -> Metric below strict threshold
- **Sample #2** (`新员工试用期转正考核流程如何发起？`): Faithfulness=0.9303, Context Recall=0.8287 -> Metric below strict threshold
- **Sample #3** (`员工病假报销及扣薪标准是怎样的？`): Faithfulness=0.9800, Context Recall=0.8793 -> Metric below strict threshold
- **Sample #4** (`公司绩效考核周期及绩效奖金发放规则是什么？`): Faithfulness=0.9000, Context Recall=0.8639 -> Metric below strict threshold
- **Sample #6** (`紧急物资采购的绿色通道触发条件是什么？`): Faithfulness=0.8711, Context Recall=0.7915 -> Metric below strict threshold
- **Sample #7** (`供应商入库资质审查需要提交哪些材料？`): Faithfulness=0.9568, Context Recall=0.8639 -> Metric below strict threshold
- **Sample #8** (`采购框架协议签定的有效期及续签流程如何规定？`): Faithfulness=0.9743, Context Recall=0.8014 -> Metric below strict threshold
- **Sample #9** (`付款流程中预付款与尾款的比例限制是多少？`): Faithfulness=0.9831, Context Recall=0.8444 -> Metric below strict threshold
- **Sample #10** (`VPN远程办公访问失败常见的排查步骤有哪些？`): Faithfulness=0.8746, Context Recall=0.8064 -> Metric below strict threshold
- **Sample #11** (`公司生产环境数据库变更的安全禁令与窗口时间是什么？`): Faithfulness=0.9630, Context Recall=0.8513 -> Metric below strict threshold
- **Sample #12** (`应用服务发生内存泄漏 (OOM) 事故的应急响应 SOP 流程？`): Faithfulness=0.8850, Context Recall=0.7558 -> Metric below strict threshold
- **Sample #13** (`开发人员申请生产环境只读权限的审批流程？`): Faithfulness=0.9052, Context Recall=0.8337 -> Metric below strict threshold
- **Sample #14** (`K8s集群微服务高可用副本数与Pod拓扑分布约束要求？`): Faithfulness=0.9133, Context Recall=0.8056 -> Metric below strict threshold
- **Sample #15** (`服务器资产盘点与报废处置的执行规范？`): Faithfulness=0.8771, Context Recall=0.8211 -> Metric below strict threshold
- **Sample #16** (`领用测试用移动终端设备的归还期限规定？`): Faithfulness=0.9640, Context Recall=0.8197 -> Metric below strict threshold
- **Sample #17** (`数据中心备品备件安全库存警告线的触发逻辑？`): Faithfulness=0.9523, Context Recall=0.8170 -> Metric below strict threshold
- **Sample #18** (`异地分公司调拨IT硬件资产的过户流转手续？`): Faithfulness=0.9904, Context Recall=0.8250 -> Metric below strict threshold
- **Sample #19** (`员工离职时办公设备退还与数据清退安全检查？`): Faithfulness=0.8171, Context Recall=0.7463 -> Metric below strict threshold
- **Sample #20** (`企业 AI 数字员工平台系统架构的核心设计原则？`): Faithfulness=0.7979, Context Recall=0.7100 -> Metric below strict threshold
- **Sample #21** (`BOOTSTRAP MODE 与 DEVELOPMENT MODE 的核心区别？`): Faithfulness=0.7886, Context Recall=0.8200 -> Metric below strict threshold
- **Sample #22** (`Harness 8 大只读证据包的存储路径与文件清单？`): Faithfulness=1.0000, Context Recall=0.8333 -> Metric below strict threshold
- **Sample #23** (`Reviewer Agent 审查代码时的通过分数线是多少？`): Faithfulness=0.7541, Context Recall=0.7403 -> Metric below strict threshold
- **Sample #24** (`Prompt Hash Cache 的原理及 Redis Key 设计？`): Faithfulness=0.8674, Context Recall=0.8185 -> Metric below strict threshold
- **Sample #25** (`LLMGateway 的模型降级 Fallback 触发条件是什么？`): Faithfulness=0.9314, Context Recall=0.7773 -> Metric below strict threshold
- **Sample #26** (`Celery 异步任务队列处理文档摄取的路由接口？`): Faithfulness=0.8400, Context Recall=0.8056 -> Metric below strict threshold
- **Sample #27** (`WebSocket 双工实时对话通道支持的事件类型有哪些？`): Faithfulness=0.9000, Context Recall=0.8444 -> Metric below strict threshold
- **Sample #28** (`Qdrant 向量数据库中使用的默认 Vector Collection 名称？`): Faithfulness=0.7600, Context Recall=0.6889 -> Metric below strict threshold
- **Sample #29** (`RAGAS 评估中 Faithfulness 指标低于 0.90 的处理动作？`): Faithfulness=0.8861, Context Recall=0.7744 -> Metric below strict threshold
