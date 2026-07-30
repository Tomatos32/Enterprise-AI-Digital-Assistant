"""Script to generate synthetic Enterprise Sample Knowledge Base (sample_kb) files."""

from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import openpyxl


def get_sample_kb_dir() -> Path:
    """Returns absolute path to docs/sample_kb directory."""
    script_dir = Path(__file__).resolve().parent
    # Product root is two levels up from backend/scripts/
    product_root = script_dir.parent.parent
    kb_dir = product_root / "docs" / "sample_kb"
    return kb_dir


def generate_markdown_files(kb_dir: Path):
    """Generates 4 modular Markdown policy files."""
    # 01_HR
    hr_content = """# 行政与人事规章说明书

> 文档编号: DOC-HR-2026-001  
> 分类: HR / 行政人事  
> 版本: v2.1  

## 1. 考勤与打卡管理制度
1. 工作时间为工作日 09:00 - 18:00，午休时间 12:00 - 13:30。
2. 员工每日须通过企业微信或前台考勤机完成上、下班打卡。
3. 迟到与早退：每月前 3 次迟到 15 分钟以内不予扣款；超过 3 次或单次迟到 30 分钟以上，按事假半天扣减薪资。

## 2. 请假类型与审批流程
- **年假**：入职满 1 年享受 5 天带薪年假。须提前至少 3 天在系统提交申请，直属主管审批通过后生效。
- **病假**：须提供二级及以上医院开具的诊断证明。每年享受 3 天带薪病假，超过部分按 80% 计发日薪。
- **事假**：按日扣减全额薪资，需直属主管及 HR 负责人双重审批。
- **婚假**：法定婚假为 3 天，符合国家规定的可享受额外假。须附结婚证复印件提前 2 周申请。

## 3. 绩效考核与奖惩
1. 公司采用 OKR + KPI 双轨绩效考核体系，每季度开展一次评估。
2. 考核结果分为 S、A、B、C 4 个等级：
   - **S 级（前 10%）**：享受 1.5 倍季度绩效奖金，优先晋升。
   - **A 级（前 30%）**：享受 1.0 倍季度绩效奖金。
   - **B 级（前 55%）**：按基准领取薪资。
   - **C 级（后 5%）**：进入 PIP 改进计划，连续 2 季度 C 级予以劝退。
"""
    (kb_dir / "01_HR_行政与人事规章.md").write_text(hr_content, encoding="utf-8")

    # 02_PROCUREMENT
    procurement_content = """# 企业采购与审批 SOP 流程规范

> 文档编号: DOC-PROC-2026-002  
> 分类: PROCUREMENT / 采购审批  
> 重点: 包含 Human-in-the-loop 金额审批阈值  

## 1. 采购申请与审批权限矩阵
公司所有办公设备、软件授权及服务外包采购均需遵循严格的金额审批权限表：

| 采购金额范围 (RMB) | 审批流程节点 | 执行动作 |
| :--- | :--- | :--- |
| **金额 <= 5,000 元** | 系统自动通过 (Auto Approve) | Agent 直接调用 `create_purchase()` 创建采购单提交 ERP |
| **5,000 元 < 金额 <= 50,000 元** | 部门主管审批 (Supervisor Approval) | Agent 触发 `Interrupt` 状态等待主管确认 (Human-in-the-loop) |
| **金额 > 50,000 元** | 部门主管 + VP + 财务总监联签 | 触发多重审批节点，需附带三家对比比价单及合同审查报告 |

## 2. 供应商资质与比价规范
1. 采购金额超过 10,000 元的物品，采购员必须提供至少 **3 家合格供应商** 的报价单与对比分析表。
2. 新加入的供应商必须提交营业执照、ISO 认证、开户许可证及近 2 年财务审计报告进行准入审核。
3. 采购合同签署须通过公司法务系统审查，违约金条款不得低于合同总金额的 20%。

## 3. 验收与付款流程
1. 货物到货后由行政部与 IT 部共同验收，填写《采购到货验收单》。
2. 凭发票、采购单、验收单在财务系统发起付款申请，财务部门在 10 个工作日内完成划款。
"""
    (kb_dir / "02_PROCUREMENT_采购与审批SOP.md").write_text(procurement_content, encoding="utf-8")

    # 03_IT
    it_content = """# IT 运维与资产借用指南

> 文档编号: DOC-IT-2026-003  
> 分类: IT / 运维资产  

## 1. IT 故障分级与服务响应 SLA
IT 运维团队对公司网络、服务器及办公设备故障实施严格的 SLA 分级响应：

- **P1 紧急故障（系统中断/核心网络瘫痪）**：
  - 响应时间: 15 分钟内
  - 恢复 SLA: 2 小时内
  - 处理动作: Agent 自动调用 `create_ticket()` 提交 P1 工单，并调用 `send_email()` 通知运维值班组。
- **P2 重要故障（局部网络故障/打印机损坏）**：
  - 响应时间: 1 小时内
  - 恢复 SLA: 8 小时内
- **P3 一般需求（软件安装/密码重置）**：
  - 响应时间: 4 小时内
  - 恢复 SLA: 24 小时内

## 2. 办公硬件设备借用与归还 SOP
1. 新员工入职首日由 IT 部门统一配备笔记本电脑、显示器与开办物资。
2. 临时借用测试机或投影仪：需通过 IT 工单系统提交申请，借用期限最长为 14 天。
3. 归还或离职交接：设备须经 IT 工程师检测无损坏、清除个人数据后方可办理归还手续。

## 3. 账号与网络安全访问权限
1. VPN 访问权限：仅限出差及居家办公人员申请，须经直属主管与 IT 安全负责人批准。
2. 密码策略：域账号密码每 90 天强制更换一次，密码长度不少于 12 位（包含大小写字母、数字及特殊字符）。
"""
    (kb_dir / "03_IT_运维与资产借用指南.md").write_text(it_content, encoding="utf-8")

    # 04_FINANCE
    finance_content = """# 财务与差旅报销标准

> 文档编号: DOC-FIN-2026-004  
> 分类: FINANCE / 财务报销  

## 1. 差旅住宿与交通补贴标准
差旅费用根据出差城市划分为一类城市（北京、上海、广州、深圳）与二类城市（其他省会及地级市）：

| 职级类别 | 一类城市住宿上限 (元/晚) | 二类城市住宿上限 (元/晚) | 伙食补贴 (元/天) | 交通工具标准 |
| :--- | :--- | :--- | :--- | :--- |
| **普通员工** | 500 元 | 350 元 | 120 元 | 高铁二等座 / 飞机经济舱 |
| **部门经理** | 800 元 | 550 元 | 180 元 | 高铁一等座 / 飞机经济舱 |
| **总监及以上** | 1,200 元 (据实报销) | 800 元 | 250 元 | 商务座 / 飞机商务舱 |

## 2. 发票抬头与开票规范
- **公司名称**：企业数字员工科技有限公司
- **纳税人识别号**：91310115MA1K99999X
- **开户银行**：招商银行上海张江支行
- **开户账号**：121908888810901

## 3. 报销提交与审核时限
1. 差旅结束或费用发生后 **15 个工作日内** 必须在财务系统提交报销申请。
2. 超期未提交报销单的，须由主管 VP 签署特批说明，否则财务部门不予受理。
3. 发票须加盖开票单位发票专用章，连同电子行程单一并作为报销凭证。
"""
    (kb_dir / "04_FINANCE_财务与差旅报销标准.md").write_text(finance_content, encoding="utf-8")


def generate_pdf_file(kb_dir: Path):
    """Generates PDF procurement SOP file."""
    pdf_dir = kb_dir / "pdf"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = pdf_dir / "采购与审批SOP_图文版.pdf"

    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.navy
    )
    story.append(Paragraph("Enterprise Procurement SOP & Approval Thresholds", title_style))
    story.append(Spacer(1, 12))

    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontSize=10,
        leading=14
    )
    story.append(Paragraph(
        "This document defines the automated vs human-in-the-loop purchasing thresholds for Enterprise AI Digital Assistant.",
        body_style
    ))
    story.append(Spacer(1, 12))

    # Table
    table_data = [
        ["Amount Range (RMB)", "Approval Node", "Action Type"],
        ["Amount <= 5,000", "Auto-Approve", "Agent invokes create_purchase() directly"],
        ["5,000 < Amount <= 50,000", "Department Manager", "Triggers Interrupt for Human-in-the-loop"],
        ["Amount > 50,000", "Manager + VP + CFO", "Multi-signature approval with 3 vendor quotes"]
    ]

    t = Table(table_data, colWidths=[150, 150, 200])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.cadetblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    story.append(t)
    doc.build(story)


def generate_excel_file(kb_dir: Path):
    """Generates Excel inventory file."""
    excel_dir = kb_dir / "excel"
    excel_dir.mkdir(parents=True, exist_ok=True)
    excel_path = excel_dir / "办公设备采购清单与库存表.xlsx"

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "设备库存明细"

    headers = ["设备编号", "设备名称", "规格型号", "单价(元)", "当前库存", "保管部门", "备注"]
    ws.append(headers)

    rows = [
        ["DEV-001", "MacBook Pro 16", "M3 Max / 36G / 1TB", 22999, 12, "IT运维部", "高阶开发专用机"],
        ["DEV-002", "Dell UltraSharp 显示器", "27英寸 4K U2723QE", 3499, 28, "行政后勤部", "标准双屏配置"],
        ["DEV-003", "Herman Miller 办公椅", "Aeron 人体工学椅", 9800, 8, "行政后勤部", "特批健康座椅"],
        ["DEV-004", "ThinkPad X1 Carbon", "i7-1370P / 32G / 1TB", 14999, 15, "IT运维部", "商务出差笔记本"],
        ["DEV-005", "Logitech MX Master 3S", "无线蓝牙鼠标 8000DPI", 699, 45, "行政后勤部", "标准外设库房"]
    ]

    for r in rows:
        ws.append(r)

    wb.save(str(excel_path))


def main():
    kb_dir = get_sample_kb_dir()
    kb_dir.mkdir(parents=True, exist_ok=True)
    print(f"Generating sample_kb files in: {kb_dir}")

    generate_markdown_files(kb_dir)
    print("[OK] Generated Markdown policy files.")

    generate_pdf_file(kb_dir)
    print("[OK] Generated PDF procurement SOP file.")

    generate_excel_file(kb_dir)
    print("[OK] Generated Excel inventory file.")

    print("Sample KB Generation Complete!")


if __name__ == "__main__":
    main()
