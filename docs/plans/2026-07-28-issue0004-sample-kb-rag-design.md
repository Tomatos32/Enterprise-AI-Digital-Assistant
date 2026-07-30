# Design Document: Enterprise AI Agent - RAG Sample Knowledge Base & Data Pipeline

> **Issue ID**: Issue-0004  
> **Date**: 2026-07-28  
> **Status**: APPROVED  
> **Target Path**: `docs/sample_kb/`  

---

## 1. Overview & Objectives

为了验证 Enterprise AI Digital Assistant 在真实企业场景下的 RAG 检索、Tool Calling 以及 Human-in-the-loop 审批流，本设计构建了一套包含多主题、多文件格式（Markdown, PDF, Excel）的规范化测试知识库。

## 2. Directory Architecture

```text
product/docs/sample_kb/
├── 01_HR_行政与人事规章.md          # 考勤、请假、绩效考核规范
├── 02_PROCUREMENT_采购与审批SOP.md   # 金额权限表、供应商标准、采购流程（含审批阈值）
├── 03_IT_运维与资产借用指南.md       # 故障报障 SLA、资产借用、权限申请
├── 04_FINANCE_财务与差旅报销标准.md   # 出差标准、发票抬头、报销时限
├── pdf/
│   └── 采购与审批SOP_图文版.pdf       # 包含复杂排版与流程规范的 PDF 格式文件
└── excel/
    └── 办公设备采购清单与库存表.xlsx  # 包含型号、单价、库存数量的结构化 Excel 数据
```

## 3. Core Business & Tool Mappings

1. **Procurement SOP (采购与审批 SOP)**:
   - 采购金额 $\le$ 5,000 元：Agent 自动创建采购单并直接提交系统（联动 `create_purchase()`）。
   - 5,000 元 $<$ 金额 $\le$ 50,000 元：需部门主管审批（触发 **Human-in-the-loop Interrupt**）。
   - 金额 $>$ 50,000 元：需 VP 及财务总监双重审批。
2. **IT Operations (IT 运维与资产指南)**:
   - 网络中断与硬件故障为 P1 级事件，必须在 15 分钟内创建工单并通知运维（联动 `create_ticket()` 及 `send_email()`）。
3. **Inventory & Purchasing (办公设备库存表)**:
   - 包含 MacBook Pro、显示器、人体工学椅等设备的库存量与采购单价（联动 `query_inventory()`）。

## 4. Loader & Chunking Pipeline

- **Markdown Loader**: 按 `#` 和 `##` 保持 Semantic Chunk，附带 Metadata（doc_id, category, title, format）。
- **PDF Loader**: 使用 PyPDF / Unstructured 提取段落与规则列表。
- **Excel Loader**: 解析 Worksheet 数据并转化为 Markdown Table 供切片与表格问答。
