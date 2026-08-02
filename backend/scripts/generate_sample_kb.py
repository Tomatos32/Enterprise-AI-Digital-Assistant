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
    """Generates 6 comprehensive enterprise Markdown policy & SOP files."""
    
    # 01_HR
    hr_content = """# 行政与人事规章说明书 (Enterprise HR & Administration Handbook)

> 文档编号: DOC-HR-2026-001  
> 分类: HR / 行政人事  
> 版本: v3.0 (2026 年度修订版)  
> 适用范围: 企业数字员工科技有限公司 全体正式员工、试用期员工及实习生  
> 密级: 内部公开 (Internal)  

---

## 1. 考勤与弹性工作制规章

### 1.1 标准工作时间与弹性打卡窗口
1. **标准工时**：公司实行 5 天 8 小时工作制。标准工作时间为工作日 **09:00 - 18:00**，午休与用餐时间为 **12:00 - 13:30**。
2. **弹性打卡窗口**：为方便员工错峰出行，公司提供 **08:30 - 09:30** 的弹性打卡窗口。员工若在 09:15 到岗打卡，下班时间相应顺延至 18:15。
3. **打卡方式**：员工每日须通过企业微信 APP（定位打卡）或园区前台人脸识别考勤机完成上、下班两次打卡。

### 1.2 迟到、早退与漏打卡处理细则
1. **迟到/早退豁免**：每位员工每月享有 **3 次 15 分钟以内** 的免扣款迟到/早退额度。
2. **超额迟到扣罚**：
   - 超过 3 次后，单次迟到 15-30 分钟，扣减当月绩效基数 50 元/次。
   - 单次迟到 30 分钟以上 2 小时以内，按事假半天扣减薪资。
   - 迟到超过 2 小时且未提前请假者，按旷工半天处理；旷工 1 天扣除 3 倍日薪。
3. **补打卡申请**：因外勤、系统故障或忘打卡者，须在 3 个工作日内于 HR 系统提交《考勤补打卡申请单》，每月补打卡不得超过 3 次，须直属主管审批通过。

---

## 2. 全量休假类型、计提矩阵与审批 SOP

### 2.1 带薪年休假 (Annual Leave) 计提矩阵
员工自入职之日起享受带薪年休假，计提标准依据累计总工龄与本公司司龄折算：

| 累计总工龄 | 在本公司司龄 | 年度带薪年假天数 | 申请提前期 requirement | 审批权限节点 |
| :--- | :--- | :--- | :--- | :--- |
| **< 1 年** | < 1 年 | 5 天 (按入职月份按比例折算) | 提前 3 天 | 直属主管审批 |
| **1 年 - 5 年** | 1 年 - 3 年 | 7 天 | 提前 3 天 | 直属主管审批 |
| **5 年 - 10 年** | 3 年 - 5 年 | 10 天 | 提前 5 天 | 直属主管 + 部门经理 |
| **>= 10 年** | >= 5 年 | 15 天 | 提前 7 天 | 直属主管 + 部门经理 + HRD |

*注：年假有效期至次年 3 月 31 日，未休完部分经 HR 特批按日薪 300% 予以补偿。*

### 2.2 带薪病假与医疗期规定
1. **带薪额度**：公司为入职员工提供每年 **5 天全额带薪病假**。
2. **凭证要求**：申请病假须在复工后 2 个工作日内上传二级及以上公立医院开具的《诊断证明书》及挂号缴费单据。
3. **医疗期薪资**：超过 5 天的病假按国家法定医疗期标准执行，病假期间发放基准工资的 80%，且不得低于当地最低工资标准的 80%。

### 2.3 婚假、产假、陪产假与育儿假
- **婚假**：法定婚假 3 天，符合国家晚婚政策及当地规定可增加至 10 天。须附结婚证复印件提前 2 周申请。
- **产假与陪产假**：女员工享受 158 天产假（难产增加 15 天）；男员工享受 15 天带薪陪产假。
- **育儿假**：子女 3 周岁以内的员工，父母双方每年各享受 10 天带薪育儿假。

### 2.4 事假与无薪假
事假按日扣减全额日薪（日薪 = 月基本工资 / 21.75）。单次事假超过 3 天须直属主管、部门 VP 及 HR 负责人三重审批。

---

## 3. 绩效考核、双轨评估与 PIP 改进机制

### 3.1 OKR + 360 度双轨绩效评估体系
1. **考核周期**：公司采用季度评估（Q1-Q4）与年度综合评定相结合的模式。
2. **评估维度**：
   - **OKR 目标达成 (60%)**：考察 Key Results 的物理完成质量、交付时间及业务价值。
   - **360 度价值观与协作 (40%)**：由直属主管 (50%)、跨部门平级 (30%) 及下属 (20%) 共同打分。

### 3.2 绩效等级正态分布与奖惩矩阵

| 绩效等级 | 分布比例 | 季度绩效奖金系数 | 职级晋升资格 | 改进/处理动作 |
| :--- | :--- | :--- | :--- | :--- |
| **S 级 (卓越)** | 前 10% | 1.5 - 2.0 倍 | 优先具备跨级晋升资格 | 纳入核心人才梯队，发放期权激励 |
| **A 级 (优秀)** | 前 30% | 1.0 - 1.2 倍 | 具备正常晋升资格 | 发放标准绩效奖金 |
| **B 级 (合格)** | 前 50% | 1.0 倍基准 | 维持当前职级 | 发放基准薪资 |
| **C 级 (需改进)** | 后 10% | 0 倍 | 冻结晋升与调薪 | 触发 90 天 PIP (绩效改进计划) |

### 3.3 PIP (Performance Improvement Plan) 90 天改善 SOP
1. **目标制定**：考核结果为 C 级的员工，须由直属主管与 HRBP 在 5 个工作日内共同制定可量化的 PIP 改进目标。
2. **中期辅导**：第 45 天进行中期 Check-in，评估完成度。
3. **终期考核**：第 90 天由绩效委员会进行终审。若 PIP 考核仍未达标，公司将依据《劳动合同法》第 40 条依法解除劳动合同。

---

## 4. 职级体系与双通道晋升 (P/M Dual Ladder)

公司设立专业序列 (P 序列) 与管理序列 (M 序列) 双通道晋升机制：

- **P 序列 (Professional)**：P4 (初级工程师) -> P5 (资深工程师) -> P6 (专家/架构师) -> P7 (资深专家) -> P8 (首席架构师) -> P9 (科学家)。
- **M 序列 (Management)**：M1 (组长) -> M2 (部门经理) -> M3 (总监) -> M4 (资深总监) -> M5 (VP)。

每年 6 月与 12 月开启两次集中晋升评审答辩，答辩委员会由 5 位 P7+/M3+ 专家组成，赞成票数 >= 4 票方可晋升。

---

## 5. 员工福利、健康保障与津贴标准

1. **补充商业医疗保险**：公司为全体全职员工购买保额 50 万元的补充商业医疗险，涵盖门诊报销 90% 及住院 100% 赔付。
2. **年度健康体检**：每年 10 月统一组织健康体检。P4-P6 员工标准为 1,200 元/人；P7+/M2+ 员工标准为 2,500 元/人，可携带 1 名家属享 5 折优惠。
3. **餐补与晚间打车**：
   - 每日发放餐补 40 元（随工资发放）。
   - 工作日加班超过 20:30，享受 30 元夜宵津贴及免费滴滴企业版打车报销。
4. **团队建设费 (Team Building)**：按 300 元/人/月 标准划拨至各部门团建账户。
"""
    (kb_dir / "01_HR_行政与人事规章.md").write_text(hr_content, encoding="utf-8")

    # 02_PROCUREMENT
    procurement_content = """# 企业采购与审批 SOP 流程规范 (Enterprise Procurement & Approval SOP)

> 文档编号: DOC-PROC-2026-002  
> 分类: PROCUREMENT / 采购审批  
> 版本: v4.2 (2026 年度修订版)  
> 重点要件: 集成 Human-in-the-loop 金额中断审批门禁与 ERP 三方对账契约  
> 密级: 内部公开 (Internal)  

---

## 1. 采购申请与多级审批权限矩阵 (Approval Threshold Matrix)

公司所有办公设备、服务器硬件、软件 SaaS 授权、云计算资源及第三方服务外包采购，均须严格遵循下述采购金额审批矩阵：

| 采购金额范围 (RMB) | 审批流程节点 (Approval Chain) | 系统控制动作 (System Action) | 招投标/比价要求 | 必需凭证与交付物 |
| :--- | :--- | :--- | :--- | :--- |
| **金额 <= 5,000 元** | 系统自动通过 (Auto Approve) | Agent 直接调用 `create_purchase()` 自动提交 ERP | 推荐 1 家合格供应商 | 电子采购申请单 |
| **5,000 < 金额 <= 50,000 元** | 部门主管单签 (Supervisor Only) | Agent 触发 `Interrupt` 挂起状态等待主管确认 (Human-in-the-loop) | 必须提供 **至少 2 家** 供应商书面报价单 | 采购申请单 + 比价单 |
| **50,000 < 金额 <= 200,000 元** | 部门主管 + 财务总监 + 采购总监 | 触发多重会签流程，校验部门季度 Budget 余额 | 必须提供 **至少 3 家** 合格供应商比价分析表 | 比价表 + 合同初稿 + 预算证明 |
| **金额 > 200,000 元** | 主管 + 财务总监 + 法务 VP + CEO + 董事会 | 必须启动线下招投标评审委员会及正式合同审计 | 强制执行正式招投标 (RFP)，评审委员会 >= 5 人 | 招投标报告 + 法务意见书 + 董事会决议 |

---

## 2. 供应商准入、准出与三方比价规范

### 2.1 供应商准入资质审查 SOP
所有新入库供应商必须通过采购部与法务部的合格供应商资质审核 (Vetting)，提交以下物理文件：
1. 营业执照副本（最新年检，注册资本不少于 200 万元 RMB）。
2. ISO9001 质量体系认证及 ISO27001 信息安全认证证书（IT/软件类供应商必具）。
3. 开户许可证及近 2 年第三方会计师事务所审计的财务报告。
4. 《反商业贿赂与廉洁合作承诺书》（法定代表人签字并加盖公章）。

### 2.2 三方比价与询价原则
1. **比价要求**：采购金额 > 10,000 元的非单一来源项目，采购员须在采购系统发起 3 家以上询价。
2. **综合评标法**：采用商务分 (40%) + 技术分 (40%) + 价格分 (20%) 综合打分，严禁低价劣质中标。

---

## 3. 采购合同审查、签署与法务合规 SOP

1. **标准合同模板**：优先使用公司法务部颁布的《标准采购合同模板 v2026》。
2. **非标合同审查**：使用供应商合同模板时，须提前 5 个工作日提交法务系统审查。
3. **核心条款阻断要求**：
   - 违约金条款：违约方须支付不少于合同总金额 **20%** 的违约金。
   - 账期要求：除 SaaS 订阅外，硬件与服务采购首付款不得高于 **30%**，尾款（不少于 **10%**）须在验收合格后支付。
   - 知识产权：外包开发产生的全量源代码与专利权归本公司独家所有。

---

## 4. 货物验收、固定资产入库与三方对账付款 SOP

### 4.1 到货验收 SOP
1. 货物到达园区后，由行政部与 IT 运维部共同在 2 个工作日内开展物理开箱验收。
2. 填写《采购到货验收单》，核对 Serial Number (SN 码)，IT 部进行固件与性能检测。
3. 单价超过 2,000 元且使用期限 > 1 年的设备，统一粘贴固定资产二维码标签并录入资产库。

### 4.2 财务三方对账与划款流程
财务部门划款前必须执行 **三方匹配 (3-Way Matching)** 校验，缺少任意一项物理凭证均予以直接拒付：

```text
[ 1. 批准的 ERP 采购单 ] + [ 2. 部门签字的到货验收单 ] + [ 3. 合规的增值税专用发票 ]
                                      │
                                      ▼
                        财务系统校验金额一致性
                                      │
                                      ▼
                    在 Net 30 天账期内完成在线划款
```

---

## 5. 紧急采购绿色通道与反腐败防线

1. **紧急采购 (Emergency Procurement)**：因线上 P0/P1 系统中断所需的服务器扩展或应急软件授权，可由 IT 负责人口头报备 VP 后先采购，24 小时内补办补签手续。
2. **廉洁审查与黑名单**：采购人员及 Agent 接口严禁接受供应商回扣。一经查实，终止合作，扣除履约保证金，并移交司法机关处理。
"""
    (kb_dir / "02_PROCUREMENT_采购与审批SOP.md").write_text(procurement_content, encoding="utf-8")

    # 03_IT
    it_content = """# IT 运维与资产借用指南 (Enterprise IT Operations & Asset SLA)

> 文档编号: DOC-IT-2026-003  
> 分类: IT / 运维资产  
> 版本: v3.5 (2026 年度修订版)  
> 适用于: 企业数字员工科技有限公司 全体员工及 IT 运维工程师  
> 密级: 内部公开 (Internal)  

---

## 1. IT 故障分级与服务响应 SLA 矩阵

IT 运维团队对公司网络、IDC 机房、vLLM 推理集群、办公电脑及企业应用故障实施严格的 SLA 分级响应与自动化工单升级机制：

| 故障等级 | 故障定义与场景范例 | 响应 SLA (Response Time) | 解决/恢复 SLA (Resolution Time) | 自动化控制动作 (Automation Action) | 升级告知节点 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **P0 (灾难级)** | 核心生产环境中断、数据丢失、全园区网络瘫痪 | **< 5 分钟** | **< 30 分钟** | 自动触发 PagerDuty 电话告警，拉起应急指挥群 | CTO + 运维总监 |
| **P1 (紧急故障)** | 局部服务器宕机、主要 API 接口错误率 > 5% | **< 15 分钟** | **< 2 小时** | Agent 自动调用 `create_ticket()` 并发送 P1 邮件 | 运维经理 + 研发总监 |
| **P2 (重要故障)** | 局部网络拥堵、重要打印机故障、编译集群变慢 | **< 1 小时** | **< 8 小时** | 自动分配至值班工程师工单池 | IT 运维组长 |
| **P3 (一般需求)** | 软件安装授权、VPN 权限申请、密码重置 | **< 4 小时** | **< 24 小时** | 自动引导自助服务机器人处理 | 值班工程师 |
| **P4 (咨询服务)** | 设备配置咨询、IT 资产借用查询 | **< 8 小时** | **< 48 小时** | 工单排队处理 | 无 |

---

## 2. 办公硬件设备全生命周期领用与归还 SOP

### 2.1 新员工入职设备标准配置矩阵

| 岗位类别 | 标准配置电脑 | 外接显示器配置 | 配套外设与办公物资 | 资产换新周期 |
| :--- | :--- | :--- | :--- | :--- |
| **研发/算法工程师** | MacBook Pro 16" (M3 Max / 36G / 1TB) 或 ThinkPad P1 | Dell 27" 4K 双屏 | 机械键盘 + 罗技 MX Master 3S | 3 年 |
| **UI/UX 设计师** | Mac Studio / iMac 27" (64G / 2TB) | Pro Display XDR / LG UltraFine | Wacom 绘图板 + 颜色校准仪 | 3 年 |
| **商务/市场/HR** | MacBook Air 15" 或 ThinkPad X1 Carbon (32G / 512G) | Dell 27" 4K 单屏 | 罗技无线键鼠套装 | 4 年 |
| **实习生/临时人员** | ThinkPad T14 (16G / 512G) | 24" 标准显示器 | 标准办公键鼠 | N/A |

### 2.2 临时设备借用 SOP
1. **申请流程**：员工因出差、测试或展会需临时借用备用机、测试机或投影仪，须提前 1 天在 IT 系统提交申请。
2. **借用期限**：单次借用期限最长为 **14 天**。超期未归还且未办理续借者，IT 系统将自动冻结该员工域账号的设备借用权限，并在当月绩效中扣减 200 元管理费。
3. **归还与数据安全擦除 SOP**：归还时由 IT 工程师现场检测硬件无损坏，并执行 DoD 5220.22-M 标准数据擦除后，办理物理归还签收。

---

## 3. 零信任网络访问 (ZTNA)、VPN 与账号安全合规

### 3.1 域账号与密码安全策略
1. **密码复杂度**：密码长度不得少于 **12 位**，必须同时包含大写字母、小写字母、数字及特殊符号（如 `@#$%^&*`）。
2. **强制更换周期**：域账号密码每 **90 天** 强制失效并要求重置，历史前 5 次旧密码不得重复使用。
3. **多因素认证 (MFA)**：登录企业邮箱、VPN 及内部服务必须强制绑定 Google Authenticator 或企业微信 MFA 动态令牌。

### 3.2 远程 VPN / ZTNA 访问规章
1. **申请门槛**：仅限出差、居家办公及紧急值班人员申请开通远程访问权限。
2. **访问审计**：远程连接会话保持最大时长为 **12 小时**，全量网络流量均经过 DLP (防泄密) 与 IDS (入侵检测) 审计。

---

## 4. 开源软件合规与密钥安全防线规章

1. **开源协议禁令**：严禁在商业产品代码库中引入 GPL / AGPL 许可协议的开源代码。
2. **硬编码密钥禁令**：源码中严禁硬编码数据库密码、API Key 或私钥证书。Pre-commit 钩子将调用 `trufflehog` 自动扫描，一经发现物理阻断 Git Push 并通报批评。
"""
    (kb_dir / "03_IT_运维与资产借用指南.md").write_text(it_content, encoding="utf-8")

    # 04_FINANCE
    finance_content = """# 财务与差旅报销标准 (Enterprise Financial & Travel Standard)

> 文档编号: DOC-FIN-2026-004  
> 分类: FINANCE / 财务报销  
> 版本: v4.0 (2026 年度修订版)  
> 适用于: 企业数字员工科技有限公司 全体出差及报销人员  
> 密级: 内部公开 (Internal)  

---

## 1. 差旅住宿与交通补贴阶梯标准矩阵

差旅费用根据出差目的城市划分为一类城市（北京、上海、广州、深圳、香港、澳门及海外主要城市）、二类城市（各省会城市、直辖市及经济特区）与三类城市（其他地级市及县级市）：

| 职级序列 (Rank) | 一类城市住宿上限 (元/晚) | 二类城市住宿上限 (元/晚) | 三类城市住宿上限 (元/晚) | 每日伙食包干补贴 (元/天) | 允许乘坐交通工具标准 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **普通员工 (P4-P6 / M1)** | 550 元 | 380 元 | 280 元 | 120 元 | 高铁二等座 / 飞机经济舱 |
| **部门经理 (P7-P8 / M2-M3)** | 850 元 | 600 元 | 450 元 | 180 元 | 高铁一等座 / 飞机经济舱 |
| **高管/VP (P9+/M4+)** | 1,500 元 (据实报销) | 1,000 元 (据实报销) | 800 元 | 280 元 | 高铁商务座 / 飞机公务舱 |

*注：淡旺季价格浮动幅度超过 20% 时，须提前在报销系统发起《超标住宿特批单》，由部门 VP 签署后方可报销。*

---

## 2. 市内交通与夜间打车报销规范

1. **差旅市内交通**：优先使用公共交通（地铁/公交），凭电子票据报销；乘坐出租车/网约车日上限为 **150 元/天**。
2. **加班打车 SOP**：工作日加班至 **20:30** 以后，或周末加班超过 4 小时，允许使用企业滴滴打车回家，费用直接由企业账户结算，无需个人垫付。

---

## 3. 商务招待费与宴请报销规范

1. **事前审批**：发起商务招待前，须在财务系统填写《商务招待事前申请单》，注明招待对象、人数、事由及预计金额。
2. **招待人均标准**：
   - 一类城市商务宴请标准：不超过 **400 元/人**（含酒水）。
   - 二类/三类城市宴请标准：不超过 **250 元/人**（含酒水）。
3. **陪餐人数限制**：客户人数在 5 人以内的，本公司陪餐人数不得超过 3 人；客户人数 > 5 人的，陪餐人数不得超过客户人数的 50%。

---

## 4. 发票开立规范与税务合规明细

公司报销发票必须严格填写完整的企业纳税人抬头信息：

- **公司全称**：企业数字员工科技有限公司
- **统一社会信用代码 (纳税人识别号)**：`91310115MA1K99999X`
- **公司注册地址与电话**：上海市浦东新区张江高科技园区科苑路 888 号 / 021-58889999
- **开户银行与账号**：招商银行上海张江支行 / `121908888810901`

*注意：发票开具内容必须为真实货物或服务明细，严禁开具“办公用品”、“会议费”等模糊统称发票。*

---

## 5. 报销提交时限、超期特批与违规处罚

1. **时限要求**：费用发生或差旅结束返回后 **15 个工作日内** 必须在财务系统完成报销单提交。
2. **超期处理**：超过 30 天未提交的报销单，须由部门 VP 及财务总监共同签署《超期报销特批说明》，超期超过 60 天不予受理。
3. **假票与违规处罚**：严禁伪造发票、重复报销或虚报行程。一经查实，追回非法所得，取消当年度绩效奖金，情节严重者直接开除。
"""
    (kb_dir / "04_FINANCE_财务与差旅报销标准.md").write_text(finance_content, encoding="utf-8")

    # 05_SECURITY
    security_content = """# 数据安全与 AI 合规使用管理制度 (Data Security & AI Safety Protocol)

> 文档编号: DOC-SEC-2026-005  
> 分类: SECURITY / 数据安全合规  
> 版本: v2.0 (2026 年度修订版)  
> 适用于: 企业数字员工科技有限公司 全体员工及合作伙伴  
> 密级: 内部公开 (Internal)  

---

## 1. 企业数据安全分级分类标准

公司将所有数据资产划分为 4 个密级，实施差异化的权限管控与加密保护：

| 密级分类 | 定义与数据范例 | 存储与传输加密要求 | 访问权限控制原则 | 违规泄漏惩罚 |
| :--- | :--- | :--- | :--- | :--- |
| **绝密 (Top Secret)** | 核心算法源码、AI 模型权重、未公开财务报表、用户核心 PII | AES-256 存储加密 / TLS 1.3 传输 / 离线物理隔离 | 仅限 CEO 及指定项目组专人，须 MFA + 审批 | 开除并移交司法机关 |
| **机密 (Confidential)** | 客户合同、采购报价单、员工薪酬数据、系统架构设计图 | 数据库行级加密 / 限制外网下载 | 部门经理及以上，基于 RBAC 动态授权 | 记大过 / 解除劳动合同 |
| **内部 (Internal)** | 内部 SOP 指南、员工通讯录、部门周报、会议纪要 | 内部网络可访问 / 禁用公共外网链接 | 全体正式员工与长期外包人员 | 警告 / 扣减当月绩效 |
| **公开 (Public)** | 官网宣传册、已公开发布的开源代码、产品新闻稿 | 无加密要求 | 所有人公开访问 | 无 |

---

## 2. 大模型 (LLM) 与 AI 数字员工合规使用防线

### 2.1 外部公有云 LLM 使用禁令
1. **代码与数据上传禁令**：严禁将公司核心业务源码、客户个人信息 (PII)、数据库连接字符串及绝密/机密文件上传至未经公司安全团队评估许可的外部公有云 AI 模型（如 ChatGPT、Claude 公共版）。
2. **脱敏要求**：如因研发测试确需向外部模型提交 Prompt，必须先通过公司内部脱敏工具过滤所有姓名、手机号、身份证号、IP 地址及密钥。

### 2.2 内部 AI 助手与 Agent 权限边界
1. **自动执行动作限制**：AI Agent 在执行写数据库、划扣资金、删除资产等破坏性动作前，必须触发 `Interrupt` 挂起，等待人类主管手写确认。
2. **审计日志留痕**：AI Agent 的所有 Thought-Action 思考链与 API 调用轨迹，均须 100% 写入不可篡改的审计日志库，留存期不少于 3 年。
"""
    (kb_dir / "05_SECURITY_数据安全与保密合规制度.md").write_text(security_content, encoding="utf-8")

    # 06_CS
    cs_content = """# 客户服务与售后支持 SOP (Customer Service & Escalation SOP)

> 文档编号: DOC-CS-2026-006  
> 分类: CS / 客户服务  
> 版本: v2.1 (2026 年度修订版)  
> 适用于: 客户服务部、技术支持部及售后运维团队  
> 密级: 内部公开 (Internal)  

---

## 1. 客服工单分级与 Upgrade 升级矩阵

客户服务团队对客户提交的咨询、投诉及故障工单实施分级响应与阶梯升级：

| 工单等级 | 响应时间 SLA | 解决时间 SLA | 初级处理人 (L1) | 二级升级节点 (L2) | 三级专家节点 (L3) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Critical (紧急故障)** | **< 10 分钟** | **< 1 小时** | L1 值班客服接单 | 15 分钟未解决升至 L2 资深技术支持 | 30 分钟升至 L3 研发架构师与产品总监 |
| **Major (重大问题)** | **< 30 分钟** | **< 4 小时** | L1 客服响应 | 1 小时升至 L2 工程师 | 2 小时升至部门经理 |
| **Minor (一般咨询)** | **< 2 小时** | **< 24 小时** | L1 客服在线解答 | N/A | N/A |

---

## 2. 客户退款与赔偿授权限额

处理客户投诉涉及经济赔偿或退款时，客服人员须在授权额度内操作：

- **L1 级客服人员**：授权直接赔偿或代金券赠送上限为 **500 元 RMB**。
- **L2 级客服主管**：授权赔偿上限为 **5,000 元 RMB**。
- **L3 级客服总监**：授权赔偿上限为 **50,000 元 RMB**，超过 50,000 元须经 CEO 批准。
"""
    (kb_dir / "06_CS_客户服务与售后支持SOP.md").write_text(cs_content, encoding="utf-8")


def generate_pdf_file(kb_dir: Path):
    """Generates a professional multi-page PDF procurement SOP file."""
    pdf_dir = kb_dir / "pdf"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = pdf_dir / "采购与审批SOP_图文版.pdf"

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#002B49'),
        alignment=1
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#555555'),
        alignment=1
    )
    story.append(Paragraph("Enterprise Procurement SOP & Approval Thresholds", title_style))
    story.append(Paragraph("Document ID: DOC-PROC-2026-002 | Version: v4.2 | Confidentiality: Internal", subtitle_style))
    story.append(Spacer(1, 16))

    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#222222')
    )
    story.append(Paragraph(
        "<b>Section 1: Automated vs Human-in-the-Loop Purchasing Thresholds</b><br/>"
        "This specification defines the strict monetary approval thresholds enforced by the Enterprise AI Digital Assistant system. "
        "Transactions within specified tiers trigger automatic API executions, Human-in-the-loop interrupts, or multi-signature executive reviews.",
        body_style
    ))
    story.append(Spacer(1, 12))

    # Table
    table_data = [
        ["Amount Range (RMB)", "Approval Node", "System Control Action", "Required Documents"],
        ["Amount <= 5,000", "Auto Approve", "Agent directly calls create_purchase()", "Purchase Request"],
        ["5,000 < Amount <= 50,000", "Supervisor Approval", "Agent triggers Interrupt for Human-in-the-loop", "PR + 2 Vendor Quotes"],
        ["50,000 < Amount <= 200,000", "Manager + CFO + Director", "Triggers multi-signature approval chain", "PR + 3 Quotes + Contract"],
        ["Amount > 200,000", "Manager + VP + CEO + Board", "Mandatory RFP & Board resolution required", "RFP Report + Board Resolution"]
    ]

    t = Table(table_data, colWidths=[120, 110, 170, 140])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F5F7FA')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
    ]))
    story.append(t)
    story.append(Spacer(1, 16))

    story.append(Paragraph(
        "<b>Section 2: 3-Way Invoice Matching & Audit SOP</b><br/>"
        "Prior to initiating financial disbursement, the accounts payable department must execute 3-Way Matching: "
        "(1) Approved Purchase Order, (2) Signed Goods Receipt Note, and (3) Validated VAT Invoice. "
        "Disbursements are executed within Net 30 payment terms upon successful matching.",
        body_style
    ))
    
    doc.build(story)


def generate_excel_file(kb_dir: Path):
    """Generates a rich multi-tab Excel asset workbook."""
    excel_dir = kb_dir / "excel"
    excel_dir.mkdir(parents=True, exist_ok=True)
    excel_path = excel_dir / "办公设备采购清单与库存表.xlsx"

    wb = openpyxl.Workbook()
    
    # Sheet 1: 设备库存明细
    ws1 = wb.active
    ws1.title = "设备库存明细"
    headers1 = ["设备编号", "设备名称", "规格型号", "单价(元)", "当前库存", "保管部门", "状态", "备注"]
    ws1.append(headers1)

    rows1 = [
        ["DEV-001", "MacBook Pro 16", "M3 Max / 36G / 1TB", 22999, 12, "IT运维部", "在库", "研发高阶专用机"],
        ["DEV-002", "Dell UltraSharp 显示器", "27英寸 4K U2723QE", 3499, 28, "行政后勤部", "在库", "标准双屏配置"],
        ["DEV-003", "Herman Miller 办公椅", "Aeron 人体工学椅", 9800, 8, "行政后勤部", "在库", "特批健康座椅"],
        ["DEV-004", "ThinkPad X1 Carbon", "i7-1370P / 32G / 1TB", 14999, 15, "IT运维部", "在库", "商务出差笔记本"],
        ["DEV-005", "Logitech MX Master 3S", "无线蓝牙鼠标 8000DPI", 699, 45, "行政后勤部", "在库", "标准外设库房"],
        ["DEV-006", "Mac Studio", "M2 Ultra / 64G / 2TB", 31999, 5, "设计部", "在库", "3D渲染工作站"],
        ["DEV-007", "Dell PowerEdge R760", "服务器 2x Xeon 6430 / 256G", 85000, 3, "IT运维部", "运行中", "IDC 本地测试节点"]
    ]
    for r in rows1:
        ws1.append(r)

    # Sheet 2: 固定资产折旧表
    ws2 = wb.create_sheet(title="固定资产折旧表")
    headers2 = ["资产编号", "资产名称", "购置日期", "原值(元)", "残值率", "折旧年限", "月折旧额(元)", "资产净值(元)"]
    ws2.append(headers2)
    rows2 = [
        ["AST-2024-001", "MacBook Pro 集体采购", "2024-01-15", 275988, "5%", 3, 7283.02, 145660.40],
        ["AST-2024-002", "Dell 显示器批次 A", "2024-03-10", 97972, "5%", 4, 1938.61, 48465.25],
        ["AST-2025-001", "IDC 服务器节点集群", "2025-06-20", 255000, "5%", 5, 4037.50, 218625.00]
    ]
    for r in rows2:
        ws2.append(r)

    # Sheet 3: 采购申请记录
    ws3 = wb.create_sheet(title="采购申请记录")
    headers3 = ["采购单号", "申请人", "申请部门", "采购物品", "估算金额(元)", "审批状态", "供应商"]
    ws3.append(headers3)
    rows3 = [
        ["PO-2026-0101", "张伟", "IT运维部", "显示器 10 台", 34990, "已完成", "戴尔中国有限公司"],
        ["PO-2026-0102", "李娜", "研发部", "MacBook Pro 5 台", 114995, "已完成", "苹果电脑贸易(上海)有限公司"],
        ["PO-2026-0103", "王强", "行政部", "人体工学椅 3 把", 29400, "审批中", "赫曼米勒家具(上海)有限公司"]
    ]
    for r in rows3:
        ws3.append(r)

    wb.save(str(excel_path))


def main():
    kb_dir = get_sample_kb_dir()
    kb_dir.mkdir(parents=True, exist_ok=True)
    print(f"Generating rich enterprise sample_kb files in: {kb_dir}")

    generate_markdown_files(kb_dir)
    print("[OK] Generated 6 comprehensive Markdown policy files.")

    generate_pdf_file(kb_dir)
    print("[OK] Generated multi-page PDF procurement SOP file.")

    generate_excel_file(kb_dir)
    print("[OK] Generated multi-tab Excel asset workbook.")

    print("Enterprise Sample KB Generation Complete!")


if __name__ == "__main__":
    main()
