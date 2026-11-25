"""Hybrid Multi-Turn Query Rewriting, Coreference Resolution & Domain-Adaptive Decomposition Engine.

Implements a 3-stage enterprise retrieval preprocessing architecture:
1. Rule Pre-processing & 6-Turn Context Analysis (filler stripping, pronoun/ellipsis detection, dynamic entity extraction)
2. Lightweight Non-Thinking LLM Contextual Rewriter (optional async path with strict timeout & callback isolation)
3. Enhanced Deterministic Multi-Turn Fallback & Universal 6-Domain Decomposition (multi-domain soft weights, zero single-domain hard lock)
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from backend.core.config import settings
from backend.core.llm import get_rewriter_llm

logger = logging.getLogger(__name__)

MAX_HISTORY_TURNS = 6
MAX_SUB_QUERIES = 5
VALID_DOMAINS = ("IT", "PROCUREMENT", "HR", "FINANCE", "SECURITY", "CS")


@dataclass
class RewrittenQuery:
    """Structured container holding rewritten standalone query, sub-queries, and soft domain weights."""

    original_query: str
    standalone_query: str
    sub_queries: List[str] = field(default_factory=list)
    primary_domain: Optional[str] = None
    extracted_entities: List[str] = field(default_factory=list)
    domains: List[str] = field(default_factory=list)
    domain_weights: Dict[str, float] = field(default_factory=dict)
    rewrite_method: str = "deterministic"
    coreference_resolved: bool = False
    anchor_topic: Optional[str] = None


# Weighted multi-domain keyword taxonomy covering all 6 enterprise policy domains.
# Note: Situational background terms like bare "出差" are intentionally excluded from FINANCE
# so IT queries such as "我出差需要临时借用备用机..." do not get cross-contaminated with FINANCE.
DOMAIN_KEYWORD_WEIGHTS: Dict[str, Dict[str, float]] = {
    "IT": {
        "备用机": 2.4,
        "临时设备": 2.2,
        "借备用机": 2.4,
        "借机": 2.2,
        "借用": 1.6,
        "外借": 1.6,
        "续借": 1.8,
        "数据擦除": 2.0,
        "归还": 1.2,
        "vpn": 2.2,
        "ztna": 2.4,
        "零信任": 2.2,
        "mfa": 2.0,
        "多因素认证": 2.0,
        "域账号": 2.2,
        "密码": 1.6,
        "故障分级": 2.2,
        "响应sla": 2.0,
        "sla": 1.5,
        "开源协议": 2.2,
        "开源软件": 2.0,
        "gpl": 2.2,
        "agpl": 2.2,
        "硬编码密钥": 2.2,
        "密钥安全": 2.0,
        "trufflehog": 2.2,
        "入职设备": 2.0,
        "标准配置电脑": 2.0,
        "设备配置": 1.8,
        "换新周期": 1.8,
        "运维": 1.8,
        "服务器": 1.4,
        "集群": 1.3,
        "故障": 1.4,
        "macbook": 1.1,
        "thinkpad": 1.1,
        "笔记本": 1.1,
        "电脑": 1.1,
        "显示器": 1.1,
        "外设": 1.2,
        "硬件": 1.2,
        "投影仪": 1.5,
        "p0": 1.4,
        "p1": 1.4,
        "p2": 1.2,
        "p3": 1.2,
        "p4": 1.2,
    },
    "PROCUREMENT": {
        "采购审批": 2.6,
        "大额采购": 2.6,
        "紧急采购": 2.4,
        "采购合同": 2.4,
        "采购": 2.2,
        "供应商": 2.4,
        "三方比价": 2.6,
        "比价": 2.2,
        "询价": 2.2,
        "招投标": 2.6,
        "招标": 2.4,
        "rfp": 2.2,
        "到货验收": 2.4,
        "验收": 1.8,
        "三方对账": 2.6,
        "三方匹配": 2.4,
        "审批矩阵": 2.4,
        "单笔审批": 2.0,
        "审批权限": 1.8,
        "审批上限": 1.8,
        "固定资产": 1.8,
        "报价单": 2.0,
        "违约金": 1.8,
        "首付款": 2.0,
        "账期": 1.8,
        "反腐败": 2.0,
        "回扣": 2.0,
        "领用": 1.0,
        "合同审查": 2.0,
    },
    "HR": {
        "行政与人事": 2.4,
        "人事": 2.0,
        "考勤": 2.2,
        "弹性打卡": 2.4,
        "补打卡": 2.2,
        "漏打卡": 2.2,
        "打卡": 1.8,
        "带薪年假": 2.4,
        "年休假": 2.4,
        "年假": 2.2,
        "带薪病假": 2.4,
        "病假": 2.2,
        "医疗期": 2.2,
        "产假": 2.4,
        "陪产假": 2.4,
        "育儿假": 2.4,
        "婚假": 2.4,
        "事假": 2.2,
        "无薪假": 2.2,
        "请假": 1.8,
        "休假": 1.8,
        "迟到": 1.8,
        "早退": 1.8,
        "旷工": 2.0,
        "绩效考核": 2.4,
        "双轨绩效": 2.4,
        "pip": 2.6,
        "绩效改进": 2.4,
        "绩效": 1.8,
        "okr": 2.0,
        "职级": 2.2,
        "双通道晋升": 2.4,
        "晋升": 2.0,
        "答辩": 1.6,
        "商业医疗险": 2.2,
        "健康体检": 2.2,
        "体检": 2.0,
        "团建费": 2.2,
        "团队建设": 2.0,
        "夜宵": 1.6,
        "试用期": 2.2,
        "转正": 2.0,
        "社保": 2.2,
        "公积金": 2.2,
        "离职": 2.0,
        "交接": 1.4,
        "薪酬": 1.8,
        "工资": 1.6,
        "调薪": 2.0,
        "年终奖": 2.0,
        "福利": 1.8,
        "工龄": 1.8,
        "司龄": 1.8,
    },
    "FINANCE": {
        "差旅报销": 2.6,
        "差旅标准": 2.6,
        "住宿标准": 2.5,
        "住宿上限": 2.5,
        "超标住宿": 2.4,
        "报销标准": 2.5,
        "报销限额": 2.4,
        "超期报销": 2.4,
        "报销": 2.4,
        "一类城市": 2.2,
        "一线城市": 2.2,
        "二类城市": 2.2,
        "二线城市": 2.2,
        "三类城市": 2.0,
        "三线城市": 2.0,
        "伙食包干": 2.2,
        "交通补贴": 2.2,
        "餐补": 1.8,
        "打车报销": 2.2,
        "加班打车": 2.2,
        "市内交通": 2.0,
        "商务招待": 2.4,
        "宴请": 2.2,
        "陪餐": 2.2,
        "纳税人识别号": 2.6,
        "税号": 2.4,
        "发票抬头": 2.4,
        "发票": 2.2,
        "开户银行": 2.0,
        "出差住宿": 2.4,
        "出差补贴": 2.4,
        "出差交通": 2.2,
        "差旅": 1.8,
        "住宿": 1.7,
        "酒店": 1.7,
        "机票": 1.8,
        "高铁": 1.8,
        "经济舱": 1.8,
        "公务舱": 1.8,
        "二等座": 1.6,
        "一等座": 1.6,
        "商务座": 1.6,
        "借款": 1.8,
        "财务": 1.8,
        "补贴": 1.4,
    },
    "SECURITY": {
        "数据安全": 2.6,
        "数据分级": 2.5,
        "安全分级": 2.4,
        "安全红线": 2.4,
        "保密合规": 2.4,
        "保密": 2.2,
        "泄密": 2.4,
        "密级": 2.2,
        "绝密": 2.4,
        "机密": 2.0,
        "脱敏": 2.4,
        "公有云大模型": 2.6,
        "外部大模型": 2.6,
        "公有云llm": 2.6,
        "外部公有云": 2.4,
        "chatgpt": 2.2,
        "pii": 2.4,
        "ai合规": 2.4,
        "权限边界": 2.0,
        "审计日志": 2.0,
        "dlp": 2.0,
        "aes-256": 2.2,
        "tls": 1.8,
        "加密": 1.6,
        "留存期": 1.6,
    },
    "CS": {
        "客户服务": 2.6,
        "客服工单": 2.6,
        "客服": 2.4,
        "售后": 2.4,
        "客户投诉": 2.6,
        "投诉": 2.2,
        "工单分级": 2.4,
        "升级矩阵": 2.2,
        "客户退款": 2.5,
        "退款": 2.2,
        "赔偿": 2.2,
        "赔付": 2.0,
        "授权限额": 2.2,
        "代金券": 2.0,
        "回访": 1.8,
        "满意度": 1.8,
        "critical": 2.0,
        "major": 1.6,
        "minor": 1.6,
        "l1": 1.5,
        "l2": 1.5,
        "l3": 1.5,
    },
}

# Backward-compatible flat domain keyword export
DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    domain: list(weights.keys()) for domain, weights in DOMAIN_KEYWORD_WEIGHTS.items()
}

# Explicit pronouns and demonstrative phrases requiring coreference resolution
PRONOUNS = [
    "这笔费用",
    "这个标准",
    "这个额度",
    "这个天数",
    "这个金额",
    "这项规定",
    "该制度",
    "该流程",
    "该设备",
    "该政策",
    "那台电脑",
    "那台设备",
    "这台电脑",
    "这台设备",
    "它们",
    "他们",
    "那个",
    "这个",
    "那台",
    "这台",
    "此项",
    "此类",
    "这种",
    "这套",
    "前述",
    "上述",
    "前者",
    "后者",
    "它",
]

# Sibling groups for parallel contrast follow-ups (e.g. "年假几天?" -> "那产假呢?")
SIBLING_GROUPS: Dict[str, List[str]] = {
    "leave": [
        "带薪年休假",
        "带薪年假",
        "年休假",
        "年假",
        "带薪病假",
        "病假",
        "陪产假",
        "产假",
        "育儿假",
        "婚假",
        "无薪假",
        "事假",
    ],
    "city_tier": [
        "一类城市",
        "一线城市",
        "二类城市",
        "二线城市",
        "三类城市",
        "三线城市",
        "北京",
        "上海",
        "广州",
        "深圳",
        "香港",
        "澳门",
    ],
    "rank": [
        "普通员工",
        "部门经理",
        "部门总监",
        "技术总监",
        "市场总监",
        "运营总监",
        "行政总监",
        "高管",
        "实习生",
        "试用期员工",
        "VP",
        "P4",
        "P5",
        "P6",
        "P7",
        "P8",
        "P9",
        "M1",
        "M2",
        "M3",
        "M4",
        "M5",
    ],
    "department": [
        "研发部",
        "市场部",
        "运营部",
        "行政部",
        "财务部",
        "人事部",
        "客服部",
        "法务部",
        "采购部",
    ],
    "severity": ["P0", "P1", "P2", "P3", "P4", "Critical", "Major", "Minor", "L1", "L2", "L3"],
    "security_level": ["绝密", "机密", "内部", "公开"],
}

# Ordered longest-first known enterprise entities (covering all 6 domains + Knowledge Graph nodes)
KNOWN_ENTITIES: List[str] = sorted(
    {
        "MacBook Pro 16",
        "MacBook Pro M3",
        "MacBook Air 15",
        "MacBook",
        "ThinkPad X1 Carbon",
        "ThinkPad P1",
        "ThinkPad T14",
        "ThinkPad",
        "4K显示器",
        "显示器",
        "笔记本",
        "备用机",
        "临时设备",
        "办公电脑",
        "研发部",
        "市场部",
        "运营部",
        "行政部",
        "财务部",
        "技术总监",
        "市场总监",
        "运营总监",
        "行政总监",
        "采购审批管理制度",
        "员工差旅标准",
        "考勤休假管理办法",
        "IT资产运维手册",
        "OA故障工单",
        "带薪年休假",
        "年假",
        "带薪病假",
        "病假",
        "产假",
        "陪产假",
        "育儿假",
        "婚假",
        "事假",
        "弹性打卡",
        "考勤",
        "绩效考核",
        "PIP",
        "职级晋升",
        "健康体检",
        "补充商业医疗保险",
        "团建费",
        "试用期",
        "社保",
        "公积金",
        "离职",
        "供应商准入",
        "三方比价",
        "招投标",
        "采购合同",
        "到货验收",
        "三方对账",
        "紧急采购",
        "固定资产",
        "采购单",
        "采购",
        "一类城市",
        "一线城市",
        "二类城市",
        "二线城市",
        "三类城市",
        "三线城市",
        "差旅报销",
        "差旅",
        "住宿标准",
        "加班打车",
        "市内交通",
        "商务招待",
        "发票",
        "纳税人识别号",
        "税号",
        "报销",
        "VPN",
        "ZTNA",
        "MFA",
        "域账号",
        "密码",
        "开源协议",
        "硬编码密钥",
        "数据安全分级",
        "数据安全",
        "外部公有云LLM",
        "外部大模型",
        "保密",
        "脱敏",
        "审计日志",
        "绝密",
        "机密",
        "客服工单",
        "客户退款",
        "客户赔偿",
        "退款",
        "赔偿",
        "售后",
        "工单",
        "权限",
        "北京",
        "上海",
        "广州",
        "深圳",
        "香港",
        "澳门",
    },
    key=lambda s: (-len(s), s),
)

# Ellipsis / follow-up attribute phrases that depend on prior turn topic when standalone subject is absent
ELLIPSIS_FOLLOWUP_PATTERNS: Tuple[str, ...] = (
    "超了",
    "超过",
    "超期",
    "逾期",
    "不还",
    "扣钱",
    "罚款",
    "处罚",
    "怎么处罚",
    "会怎样",
    "怎么办",
    "怎么处理",
    "怎么申请",
    "如何申请",
    "怎么办理",
    "怎么报销",
    "怎么算",
    "怎么审批",
    "如何审批",
    "需要谁审批",
    "谁审批",
    "谁来审批",
    "审批流程",
    "需要什么材料",
    "需要什么凭证",
    "什么凭证",
    "什么材料",
    "要交押金",
    "交押金",
    "押金",
    "有效期",
    "最长多久",
    "多久",
    "几天",
    "限额",
    "上限",
    "标准是多少",
    "住宿标准",
    "餐补",
    "补贴",
    "参考单价",
    "多少钱",
    "单价",
    "流程是什么",
    "有什么要求",
    "条件是什么",
    "响应时间",
    "解决时间",
    "触发什么",
)

FOLLOWUP_LEAD_RE = re.compile(r"^(那|那么|如果|要是|假如|还有|另外|顺便|再问下|再问一下|请问那|可是|但是)")
FOLLOWUP_TAIL_RE = re.compile(r"(呢|吗|么|怎么样|怎么算|多少|多久|谁审批|怎么办)[？?！!。]*$")
FILLER_PREFIX_RE = re.compile(
    r"^(请问|你好|您好|嗨|麻烦问下|麻烦请问|我想了解一下|我想了解|我想问一下|我想问|帮我查一下|帮我查查|查一下|查询一下|告诉我)[，,、：:\s]*"
)

# Domain-adaptive expansion rules: (domain, trigger_keywords, expanded_search_query)
DOMAIN_FACET_EXPANSIONS: List[Tuple[str, Tuple[str, ...], str]] = [
    # HR
    ("HR", ("年假", "年休假"), "带薪年休假 计提矩阵 工龄 司龄 天数 有效期 审批"),
    ("HR", ("病假", "医疗期"), "带薪病假 5天 医疗期 诊断证明 基准工资"),
    ("HR", ("产假", "陪产假", "育儿假", "婚假"), "婚假 产假 158天 陪产假 15天 育儿假 10天 申请"),
    ("HR", ("事假", "无薪假"), "事假 无薪假 日薪扣减 超过3天 三重审批"),
    ("HR", ("迟到", "早退", "旷工", "打卡", "考勤"), "考勤 弹性打卡窗口 迟到豁免 补打卡 扣罚 旷工"),
    ("HR", ("绩效", "pip", "okr", "360"), "OKR 360度 绩效等级 正态分布 奖金系数 PIP 90天改善"),
    ("HR", ("职级", "晋升", "答辩"), "P序列 M序列 双通道晋升 6月 12月 评审答辩"),
    ("HR", ("体检", "医疗险", "福利", "团建", "夜宵"), "补充商业医疗保险 年度健康体检 餐补 晚间打车 团队建设费"),
    ("HR", ("试用期", "转正", "社保", "公积金", "离职"), "行政与人事规章 试用期 正式员工 社保 离职 劳动合同"),
    # PROCUREMENT
    ("PROCUREMENT", ("审批", "额度", "上限", "矩阵", "cfo", "vp", "大额"), "采购申请 多级审批权限矩阵 5000 50000 200000 主管 财务总监 CFO VP"),
    ("PROCUREMENT", ("供应商", "准入", "资质"), "供应商准入资质审查 营业执照 ISO9001 ISO27001 审计报告"),
    ("PROCUREMENT", ("比价", "询价", "招标", "招投标", "rfp"), "三方比价 询价原则 综合评标法 招投标 RFP 报价单"),
    ("PROCUREMENT", ("合同", "违约金", "首付款", "账期", "法务"), "采购合同审查 法务合规 违约金 20% 首付款 30% 尾款 知识产权"),
    ("PROCUREMENT", ("验收", "到货", "固定资产", "对账", "划款"), "到货验收 固定资产标签 财务三方对账 3-Way Matching Net 30 划款"),
    ("PROCUREMENT", ("紧急采购", "绿色通道", "回扣", "反腐败"), "紧急采购 绿色通道 24小时补签 廉洁审查 反腐败 黑名单"),
    # IT (non-borrowing facets; borrowing facets handled with specialized precision)
    ("IT", ("入职设备", "标准配置", "换新周期", "新员工"), "新员工入职设备 标准配置矩阵 MacBook ThinkPad 显示器 换新周期"),
    ("IT", ("故障", "sla", "p0", "p1", "p2", "p3", "p4", "响应"), "IT故障分级 服务响应SLA矩阵 P0 P1 P2 P3 P4 响应时间 恢复时间"),
    ("IT", ("vpn", "ztna", "零信任", "远程"), "远程VPN ZTNA 访问规章 申请门槛 12小时 DLP IDS 审计"),
    ("IT", ("密码", "域账号", "mfa", "多因素"), "域账号 密码复杂度 12位 90天更换 MFA 动态令牌"),
    ("IT", ("开源协议", "开源软件", "gpl", "agpl", "密钥", "硬编码", "trufflehog"), "开源软件合规 GPL AGPL 禁令 硬编码密钥 trufflehog 阻断"),
    # FINANCE
    ("FINANCE", ("住宿", "酒店", "差旅", "一类城市", "一线城市", "二类城市", "二线城市", "三类城市", "三线城市", "机票", "高铁", "补贴", "餐补"), "差旅住宿与交通补贴阶梯标准矩阵 一类城市 二类城市 三类城市 住宿上限 伙食包干 高铁 飞机"),
    ("FINANCE", ("打车", "市内交通", "网约车", "滴滴", "加班"), "市内交通 150元 夜间打车 加班打车 20:30 企业滴滴"),
    ("FINANCE", ("招待", "宴请", "陪餐"), "商务招待费 宴请报销 事前申请 400元 250元 陪餐人数限制"),
    ("FINANCE", ("发票", "税号", "抬头", "纳税人", "开户银行"), "发票开立规范 纳税人识别号 税号 公司抬头 开户银行 账号"),
    ("FINANCE", ("时限", "超期", "假票", "违规", "报销"), "报销提交时限 15个工作日 超期30天 60天 特批 违规处罚"),
    # SECURITY
    ("SECURITY", ("分级", "密级", "绝密", "机密", "加密", "泄密", "保密"), "企业数据安全分级分类标准 绝密 机密 内部 公开 AES-256 TLS 权限 泄漏惩罚"),
    ("SECURITY", ("大模型", "llm", "chatgpt", "公有云", "脱敏", "pii", "ai", "agent", "审计日志"), "外部公有云LLM使用禁令 脱敏 PII 内部AI助手 Agent权限边界 Interrupt 审计日志 3年"),
    # CS
    ("CS", ("客服", "工单", "升级", "sla", "critical", "major", "minor", "l1", "l2", "l3", "售后"), "客服工单分级 升级矩阵 Critical Major Minor 响应SLA L1 L2 L3"),
    ("CS", ("退款", "赔偿", "赔付", "投诉", "代金券", "限额"), "客户退款 赔偿授权限额 L1 500元 L2 5000元 L3 50000元 CEO"),
]

_REWRITER_SYSTEM_PROMPT = """你是企业知识检索的多轮上下文 Query 改写器。仅输出合法 JSON，禁止输出多余解释：
{
  "standalone_query": "补全指代与省略后的简洁独立问句（不超过35字，保留原始实体、数字、城市、职级或自定义术语）",
  "sub_queries": ["简洁检索子句1", "简洁检索子句2"],
  "domains": ["仅限 IT/PROCUREMENT/HR/FINANCE/SECURITY/CS，按相关性排序，无归属返回 []"],
  "entities": ["核心实体或自定义术语"],
  "coreference_resolved": true或false
}

规则：
1. 若当前提问已自包含（换了新话题且无代词/省略），禁止拼接历史无关话题，coreference_resolved=false。
2. 遇到代词（它、这个、那台等）或无代词省略（“那产假呢？”、“二线城市呢？”、“超了会怎样？”），必须结合历史精准补全。
3. 跨领域复合提问时，domains 列出全部涉及领域，sub_queries 拆分为 2~4 条简洁短句。
4. 仅在真正询问报销/住宿/交通补贴/发票时才加 FINANCE；严禁把仅作背景的“出差”改写为“差旅政策”或加入 FINANCE。
5. 完整保留自定义文档专有名词（如 A100、GPU集群配额）。"""


def _extract_recent_history(
    history: Optional[Sequence[BaseMessage]],
    max_turns: int = MAX_HISTORY_TURNS,
) -> List[Tuple[str, str]]:
    """Extracts up to max_turns recent (role, text) pairs from LangChain message history."""
    if not history:
        return []

    max_msgs = max(2, max_turns * 2)
    recent = list(history)[-max_msgs:]
    result: List[Tuple[str, str]] = []
    for msg in recent:
        content = getattr(msg, "content", "")
        text = content if isinstance(content, str) else str(content)
        text = text.strip()
        if not text:
            continue
        if isinstance(msg, HumanMessage):
            role = "user"
        elif isinstance(msg, AIMessage):
            role = "assistant"
        else:
            msg_type = str(getattr(msg, "type", "")).lower()
            role = "user" if msg_type == "human" else ("assistant" if msg_type == "ai" else "system")
        if role == "system":
            continue
        result.append((role, text[:400]))
    return result


def _dedupe_preserve_order(items: Sequence[str]) -> List[str]:
    """Deduplicates non-empty strings while preserving original order."""
    seen: set[str] = set()
    output: List[str] = []
    for item in items:
        cleaned = item.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            output.append(cleaned)
    return output


def _extract_entities_from_text(text: str) -> List[str]:
    """Extracts both known enterprise entities and dynamic custom-document topic phrases."""
    if not text:
        return []

    found: List[str] = []
    text_lower = text.lower()

    # 1. Known enterprise vocabulary (longest-first to preserve specificity e.g. MacBook Pro 16)
    for entity in KNOWN_ENTITIES:
        if entity.lower() in text_lower:
            # Skip shorter entity if already covered as substring of a longer matched entity
            if any(entity.lower() in existing.lower() for existing in found):
                continue
            found.append(entity)

    # 2. Quoted document or policy titles: 《...》
    for title in re.findall(r"《([^《》]{2,36})》", text):
        cleaned_title = title.strip()
        if cleaned_title and cleaned_title not in found:
            found.append(cleaned_title)

    # 3. Dynamic custom policy / system / hardware terms (supports arbitrary uploaded docs)
    dynamic_patterns = [
        r"([A-Za-z][A-Za-z0-9_-]{1,15}\s*[一-龥]{2,8}(?:节点|集群|配额|服务器|模型|系统|卡|工具))",
        r"([一-龥A-Za-z0-9]{2,14}(?:配额制度|管理制度|补充通知|管理办法|实施细则|规章制度|操作指南|SOP|方案|政策))",
        r"([一-龥]{2,8}(?:集群|算力节点|审批委员会|绿色通道))",
    ]
    for pattern in dynamic_patterns:
        for match in re.findall(pattern, text):
            candidate = re.sub(
                r"^(请问|公司|企业|关于|申请|查询|了解|这个|那个|我的|咱们|超过|超出|高于|低于|达到)",
                "",
                match.strip(),
            ).strip()
            if len(candidate) >= 3 and not any(candidate.lower() in e.lower() for e in found):
                found.append(candidate)

    return _dedupe_preserve_order(found)[:10]


def _find_sibling_in_group(text: str, group_name: str) -> Optional[str]:
    """Finds a matching sibling term from a specific SIBLING_GROUPS bucket (longest-first)."""
    terms = SIBLING_GROUPS.get(group_name, [])
    t_lower = text.lower()
    for term in sorted(terms, key=lambda s: (-len(s), s)):
        if term.lower() in t_lower:
            if term.isascii():
                if re.search(rf"(?<![a-z0-9]){re.escape(term.lower())}(?![a-z0-9])", t_lower):
                    return term
            else:
                return term
    return None


def _find_all_sibling_matches(text: str) -> List[Tuple[str, str]]:
    """Finds all (group_name, sibling_term) pairs present in text across all sibling groups."""
    matches: List[Tuple[str, str]] = []
    for group_name in SIBLING_GROUPS:
        hit = _find_sibling_in_group(text, group_name)
        if hit is not None:
            matches.append((group_name, hit))
    return matches


def _parse_llm_rewriter_json(raw_text: str) -> Optional[Dict[str, Any]]:
    """Robustly extracts and validates JSON payload from LLM contextual rewriter output."""
    if not raw_text or not isinstance(raw_text, str):
        return None

    cleaned = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL | re.IGNORECASE).strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, flags=re.DOTALL)
    if fence_match:
        candidate = fence_match.group(1)
    else:
        brace_match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not brace_match:
            return None
        candidate = brace_match.group(0)

    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return None

    if not isinstance(parsed, dict):
        return None

    standalone = str(parsed.get("standalone_query") or "").strip()
    if not standalone or len(standalone) > 240:
        return None

    raw_subs = parsed.get("sub_queries")
    sub_queries: List[str] = []
    if isinstance(raw_subs, list):
        for item in raw_subs:
            s = str(item or "").strip()
            if s and len(s) <= 180:
                sub_queries.append(s)
    sub_queries = _dedupe_preserve_order(sub_queries)[:MAX_SUB_QUERIES]

    raw_domains = parsed.get("domains")
    domains: List[str] = []
    if isinstance(raw_domains, list):
        for dom in raw_domains:
            d = str(dom or "").strip().upper()
            if d in VALID_DOMAINS and d not in domains:
                domains.append(d)

    raw_entities = parsed.get("entities")
    entities: List[str] = []
    if isinstance(raw_entities, list):
        for ent in raw_entities:
            e = str(ent or "").strip()
            if e and len(e) <= 60:
                entities.append(e)
    entities = _dedupe_preserve_order(entities)[:10]

    coref = bool(parsed.get("coreference_resolved", False))

    return {
        "standalone_query": standalone,
        "sub_queries": sub_queries,
        "domains": domains,
        "entities": entities,
        "coreference_resolved": coref,
    }


class QueryRewriter:
    """Enterprise Hybrid Multi-Turn Query Rewriter & Multi-Domain Decomposer."""

    def __init__(self) -> None:
        pass

    def _score_domains(self, query: str) -> Tuple[List[str], Dict[str, float]]:
        """Computes multi-domain relevance scores and normalized soft weights without single-domain hard locks."""
        q_lower = query.lower()
        raw_scores: Dict[str, float] = {}

        for domain, kw_map in DOMAIN_KEYWORD_WEIGHTS.items():
            matched_kws: List[str] = []
            score = 0.0
            # Match longest keywords first so compound terms (e.g. "差旅报销") aren't double-counted with substrings ("报销")
            for kw in sorted(kw_map.keys(), key=len, reverse=True):
                kw_l = kw.lower()
                if any(kw_l in prev for prev in matched_kws):
                    continue
                if kw_l.isascii():
                    hit = bool(re.search(rf"(?<![a-z0-9]){re.escape(kw_l)}(?![a-z0-9])", q_lower))
                else:
                    hit = kw_l in q_lower
                if hit:
                    matched_kws.append(kw_l)
                    score += kw_map[kw]
            if score > 0.0:
                raw_scores[domain] = round(score, 4)

        if not raw_scores:
            return [], {}

        sorted_items = sorted(raw_scores.items(), key=lambda x: x[1], reverse=True)
        max_score = sorted_items[0][1]

        # Retain all meaningful domains (either >= 1.4 absolute or >= 35% of top domain score)
        domains: List[str] = []
        weights: Dict[str, float] = {}
        for dom, sc in sorted_items:
            ratio = sc / max_score if max_score > 0 else 0.0
            if sc >= 1.4 or ratio >= 0.35:
                domains.append(dom)
                weights[dom] = round(min(1.0, max(0.35, ratio)), 4)

        return domains, weights

    def _detect_primary_domain(self, query: str) -> Optional[str]:
        """Returns the highest-weighted domain (backward-compatible helper without hard single-domain lock)."""
        domains, _ = self._score_domains(query)
        return domains[0] if domains else None

    def _is_elliptical_fragment(self, text: str) -> bool:
        """Detects whether a prior user message was itself a terse elliptical follow-up."""
        cleaned = text.strip()
        if len(cleaned) <= 8 and bool(FOLLOWUP_TAIL_RE.search(cleaned)):
            return True
        if len(cleaned) <= 10 and bool(FOLLOWUP_LEAD_RE.search(cleaned)) and bool(FOLLOWUP_TAIL_RE.search(cleaned)):
            return True
        return False

    def _extract_anchor_from_history(
        self,
        recent_history: List[Tuple[str, str]],
    ) -> Tuple[Optional[str], Optional[str], List[str]]:
        """Extracts (anchor_entity, question_template, recent_entities) from recent conversation history.

        - anchor_entity comes from the most recent turn so attribute/pronoun follow-ups bind to the latest topic.
        - question_template skips terse elliptical user turns (e.g. '那产假呢？') so 3-turn sibling chains
          inherit the full framing question (e.g. '公司年假有几天？').
        """
        last_user_query: Optional[str] = None
        question_template: Optional[str] = None
        user_entities: List[str] = []
        assistant_entities: List[str] = []

        for role, text in reversed(recent_history):
            ents = _extract_entities_from_text(text)
            if role == "user":
                stripped = FILLER_PREFIX_RE.sub("", text).strip() or text
                if last_user_query is None and len(stripped) >= 3:
                    last_user_query = stripped
                if question_template is None and len(stripped) >= 5 and not self._is_elliptical_fragment(stripped):
                    question_template = stripped
                if ents and not user_entities:
                    user_entities = ents
            elif role == "assistant" and ents and not assistant_entities:
                assistant_entities = ents

            if question_template and user_entities:
                break

        effective_template = question_template or last_user_query
        combined_entities = _dedupe_preserve_order(user_entities + assistant_entities)
        anchor_entity = combined_entities[0] if combined_entities else None

        # If no named entity matched (e.g. a brand-new arbitrary topic in user history), build a compact phrase anchor
        if not anchor_entity and effective_template:
            compact = re.sub(r"[？?！!。，,].*$", "", effective_template).strip()
            compact = re.sub(r"(是多少|怎么算|怎么办|有哪些|有什么|怎么申请|谁审批|多久|几天)$", "", compact).strip()
            if 2 <= len(compact) <= 24:
                anchor_entity = compact

        return anchor_entity, effective_template, combined_entities

    def _resolve_coreference(
        self,
        query: str,
        history: Optional[List[BaseMessage]] = None,
    ) -> str:
        """Backward-compatible wrapper returning the resolved standalone query string."""
        resolved, _, _ = self._resolve_context_and_ellipsis(query, history)
        return resolved

    def _resolve_context_and_ellipsis(
        self,
        query: str,
        history: Optional[List[BaseMessage]] = None,
    ) -> Tuple[str, bool, Optional[str]]:
        """Resolves explicit pronouns, parallel sibling switches, and implicit ellipsis follow-ups."""
        cleaned_query = query.strip()
        recent_history = _extract_recent_history(history, max_turns=MAX_HISTORY_TURNS)
        if not recent_history or not cleaned_query:
            return cleaned_query, False, None

        anchor_entity, last_user_query, recent_entities = self._extract_anchor_from_history(recent_history)
        current_entities = _extract_entities_from_text(cleaned_query)
        current_domains, _ = self._score_domains(cleaned_query)

        # Case 1: Explicit pronouns / demonstratives
        matched_pronouns = [p for p in PRONOUNS if p in cleaned_query]
        if matched_pronouns and anchor_entity:
            resolved = cleaned_query
            for pronoun in matched_pronouns:
                if pronoun not in resolved:
                    continue
                if pronoun in ("那台电脑", "这台电脑", "那台设备", "这台设备"):
                    replacement = (
                        f"{anchor_entity}电脑"
                        if "电脑" in pronoun and "电脑" not in anchor_entity
                        else anchor_entity
                    )
                elif pronoun in ("那台", "这台"):
                    replacement = f"{anchor_entity}"
                elif pronoun in ("这个额度", "这个标准", "这个天数", "这个金额"):
                    suffix = pronoun[2:]
                    replacement = f"{anchor_entity}{suffix}"
                else:
                    replacement = anchor_entity
                resolved = resolved.replace(pronoun, replacement, 1)
            logger.info("[QueryRewriter] Pronoun coreference resolved: '%s' -> '%s'", query, resolved)
            return resolved, True, anchor_entity

        # Case 2: Parallel sibling substitution (e.g. "年假几天?" -> "那产假呢?", "一线城市住宿标准?" -> "二线城市呢?")
        is_short_or_elliptical = (
            len(cleaned_query) <= 18
            or bool(FOLLOWUP_LEAD_RE.search(cleaned_query))
            or bool(FOLLOWUP_TAIL_RE.search(cleaned_query))
        )
        if is_short_or_elliptical and last_user_query:
            curr_siblings = _find_all_sibling_matches(cleaned_query)
            for group_name, new_term in curr_siblings:
                old_term = _find_sibling_in_group(last_user_query, group_name)
                if not old_term or new_term.lower() == old_term.lower():
                    continue
                # Only substitute when current query is genuinely elliptical (not a complete new multi-clause question)
                non_sibling_body = re.sub(
                    r"^(那|那么|如果|要是|还有|另外|请问|如果是|换成)",
                    "",
                    cleaned_query,
                )
                non_sibling_body = re.sub(re.escape(new_term), "", non_sibling_body, flags=re.IGNORECASE)
                non_sibling_body = re.sub(r"[的呢吗么呀吧？?！!。，,\s]+", "", non_sibling_body)
                if len(non_sibling_body) <= 6:
                    substituted = re.sub(
                        re.escape(old_term),
                        new_term,
                        last_user_query,
                        count=1,
                        flags=re.IGNORECASE,
                    )
                    if non_sibling_body and non_sibling_body not in substituted:
                        substituted = f"{substituted} ({non_sibling_body})"
                    logger.info(
                        "[QueryRewriter] Parallel sibling ellipsis resolved (%s: %s -> %s): '%s' -> '%s'",
                        group_name,
                        old_term,
                        new_term,
                        query,
                        substituted,
                    )
                    return substituted, True, new_term

        # Case 3: Implicit ellipsis attribute / constraint continuation (no pronouns)
        # Examples: "住宿标准是多少？" after "去北京出差"; "超了会怎样？" after "借备用机最长几天"; "需要谁审批？" after "GPU配额"
        has_ellipsis_cue = any(cue in cleaned_query for cue in ELLIPSIS_FOLLOWUP_PATTERNS)
        has_followup_syntax = bool(FOLLOWUP_LEAD_RE.search(cleaned_query)) or (
            len(cleaned_query) <= 14 and bool(FOLLOWUP_TAIL_RE.search(cleaned_query))
        )

        # Topic-switch guard: if the user introduces a distinct domain & concrete subject entity unrelated to history, do NOT pollute
        prev_domains, _ = self._score_domains(last_user_query or " ".join(recent_entities))
        is_distinct_self_contained_topic = (
            bool(current_entities)
            and bool(current_domains)
            and not any(d in prev_domains for d in current_domains)
            and not bool(FOLLOWUP_LEAD_RE.search(cleaned_query))
            and len(cleaned_query) >= 10
        )
        if is_distinct_self_contained_topic:
            return cleaned_query, False, None

        # Special situational carry-over: prior turn sets trip/city/department/custom-doc context, current asks attribute
        generic_attribute_entities = {"住宿标准", "报销", "审批", "标准", "限额", "上限", "额度", "金额", "期限", "配额"}
        missing_subject = not current_entities or (
            all(ent in generic_attribute_entities for ent in current_entities)
            and len(cleaned_query) <= 14
        )
        if anchor_entity and (has_ellipsis_cue or has_followup_syntax) and missing_subject:
            if anchor_entity.lower() not in cleaned_query.lower():
                # Build concise contextual anchor (include secondary context like city/department if relevant)
                context_parts = [anchor_entity]
                if last_user_query and "出差" in last_user_query and "出差" not in anchor_entity and "出差" not in cleaned_query:
                    context_parts.append("出差")
                prefix = "".join(context_parts) if len(context_parts) <= 2 else " ".join(context_parts[:2])
                # Normalize conversational lead-in like "那超了会怎样？" -> "<anchor> 超了会怎样？"
                stripped_lead = re.sub(r"^(那|那么|还有|另外)[，,\s]*", "", cleaned_query).strip() or cleaned_query
                resolved = f"{prefix} {stripped_lead}"
                logger.info("[QueryRewriter] Implicit ellipsis resolved: '%s' -> '%s'", query, resolved)
                return resolved, True, anchor_entity

        return cleaned_query, False, None

    def _split_clauses(self, cleaned: str) -> List[str]:
        """Splits a compound sentence into meaningful clauses across punctuation and conjunctions."""
        # Protect decimals/numbers and split on strong clause separators
        by_punct = [c.strip() for c in re.split(r"[，,。；;？?！!]+", cleaned) if len(c.strip()) >= 2]
        clauses: List[str] = []
        conj_re = re.compile(r"(?:并且|同时|以及|另外|还有|顺便问下|并按|以及按|并)")
        for segment in by_punct:
            parts = [p.strip() for p in conj_re.split(segment) if len(p.strip()) >= 3]
            if len(parts) > 1:
                clauses.extend(parts)
            else:
                clauses.append(segment)
        return _dedupe_preserve_order(clauses)

    def _build_borrowing_sub_queries(self, cleaned: str, core_entity: str) -> List[str]:
        """Generates high-precision facet sub-queries for temporary IT device borrowing."""
        facets: List[str] = []
        if any(k in cleaned for k in ("期限", "多久", "几天", "时间", "借多久")):
            facets.append("借用期限 最长时间 申请时限")
        if any(k in cleaned for k in ("押金", "保证金", "交钱", "抵押")):
            facets.append("押金 费用 保证金")
        if any(k in cleaned for k in ("超期", "超借用期限", "超了", "逾期", "不还", "违约", "扣钱", "罚款", "失信", "扣减")):
            facets.append("超期 续借 冻结权限 绩效扣减 管理费")
        if any(k in cleaned for k in ("归还", "交回", "擦除", "数据安全")):
            facets.append("归还流程 数据安全擦除")

        subs = [f"{core_entity} {facet}" for facet in facets]
        if subs or any(k in cleaned for k in ("备用机", "借机", "借用", "临时设备")):
            subs.append(f"IT运维与资产借用指南 {core_entity} 临时设备借用SOP")
        return subs

    def _split_sub_queries(
        self,
        query: str,
        domain: Optional[str],
        domains: Optional[List[str]] = None,
    ) -> List[str]:
        """Decomposes single-domain, cross-domain, and open-domain queries into atomic search sub-queries."""
        cleaned = FILLER_PREFIX_RE.sub("", query).strip() or query.strip()
        q_lower = cleaned.lower()
        target_domains = list(domains) if domains else ([domain] if domain else [])

        sub_queries: List[str] = []

        # 1. Specialized high-precision IT temporary borrowing decomposition
        is_temp_borrow = any(k in cleaned for k in ("备用机", "借机", "借用机", "临时电脑", "临时设备")) or (
            any(k in cleaned for k in ("借用", "外借"))
            and any(k in q_lower for k in ("电脑", "笔记本", "macbook", "thinkpad", "投影仪"))
        )
        if is_temp_borrow:
            borrow_entity = "备用机" if any(k in cleaned for k in ("备用机", "借机", "借用机", "临时电脑")) else "办公电脑"
            sub_queries.extend(self._build_borrowing_sub_queries(cleaned, borrow_entity))

        # 2. Cross-domain & multi-clause decomposition
        clauses = self._split_clauses(cleaned)
        if len(target_domains) >= 2:
            # Ensure every matched domain gets explicit targeted sub-queries (prevents domain starvation)
            for clause in clauses:
                clause_domains, _ = self._score_domains(clause)
                if clause_domains:
                    sub_queries.append(clause)
            for dom in target_domains:
                for rule_dom, triggers, expansion in DOMAIN_FACET_EXPANSIONS:
                    if rule_dom == dom and any(t in q_lower for t in triggers):
                        sub_queries.append(expansion)
                        break
        else:
            # Single-domain or general custom-doc decomposition
            active_dom = target_domains[0] if target_domains else None
            if active_dom and not is_temp_borrow:
                for rule_dom, triggers, expansion in DOMAIN_FACET_EXPANSIONS:
                    if rule_dom == active_dom and any(t in q_lower for t in triggers):
                        sub_queries.append(expansion)
                        if len(sub_queries) >= 3:
                            break

            if not sub_queries:
                if len(clauses) > 1:
                    # Carry main subject onto short follow-up clauses for self-contained retrieval
                    primary_entities = _extract_entities_from_text(clauses[0])
                    lead_anchor = primary_entities[0] if primary_entities else ""
                    for idx, clause in enumerate(clauses):
                        if idx > 0 and lead_anchor and lead_anchor.lower() not in clause.lower() and len(clause) <= 14:
                            sub_queries.append(f"{lead_anchor} {clause}")
                        else:
                            sub_queries.append(clause)
                else:
                    sub_queries.append(cleaned)
            elif len(clauses) > 1 and not is_temp_borrow:
                # Retain the original meaningful clauses alongside normalized expansions
                for clause in clauses[:2]:
                    if len(clause) >= 4:
                        sub_queries.append(clause)

        deduped = _dedupe_preserve_order(sub_queries)
        return deduped[:MAX_SUB_QUERIES] if deduped else [cleaned]

    def rewrite(
        self,
        query: str,
        history: Optional[List[BaseMessage]] = None,
    ) -> RewrittenQuery:
        """Executes synchronous deterministic multi-turn query rewriting and multi-domain decomposition."""
        standalone_q, coref_resolved, anchor_topic = self._resolve_context_and_ellipsis(query, history)
        domains, domain_weights = self._score_domains(standalone_q)
        primary_domain = domains[0] if domains else None
        sub_queries = self._split_sub_queries(standalone_q, primary_domain, domains=domains)
        extracted_entities = _extract_entities_from_text(standalone_q)

        logger.info(
            "[QueryRewriter] Deterministic rewrite: '%s' -> '%s' | Domains=%s | Sub-queries=%s",
            query,
            standalone_q,
            domains,
            sub_queries,
        )

        return RewrittenQuery(
            original_query=query,
            standalone_query=standalone_q,
            sub_queries=sub_queries,
            primary_domain=primary_domain,
            extracted_entities=extracted_entities,
            domains=domains,
            domain_weights=domain_weights,
            rewrite_method="deterministic",
            coreference_resolved=coref_resolved,
            anchor_topic=anchor_topic,
        )

    def _should_use_llm(
        self,
        query: str,
        recent_history: List[Tuple[str, str]],
        det_result: RewrittenQuery,
    ) -> bool:
        """Decides whether invoking the lightweight non-thinking LLM adds contextual value."""
        if not getattr(settings, "QUERY_REWRITER_LLM_ENABLED", True):
            return False
        if not query or len(query.strip()) < 2:
            return False
        # Multi-turn conversations, cross-domain queries, or unmapped open-domain queries benefit from LLM rewriting
        if recent_history:
            return True
        if len(det_result.domains) >= 2 or not det_result.domains:
            return True
        if len(query.strip()) >= 16:
            return True
        return False

    def _build_llm_messages(
        self,
        query: str,
        recent_history: List[Tuple[str, str]],
        data_source: Optional[str] = None,
    ) -> List[BaseMessage]:
        """Builds compact prompt messages for the non-thinking contextual query rewriter LLM."""
        lines: List[str] = []
        if recent_history:
            lines.append("【最近对话历史】:")
            for role, text in recent_history:
                label = "用户" if role == "user" else "助手"
                lines.append(f"{label}: {text}")
        if data_source:
            lines.append(f"【关联数据源】: {data_source}")
        lines.append(f"【当前用户输入】: {query}")

        return [
            SystemMessage(content=_REWRITER_SYSTEM_PROMPT),
            HumanMessage(content="\n".join(lines)),
        ]

    async def _invoke_rewriter_llm(
        self,
        prompt_messages: List[BaseMessage],
        timeout_sec: float,
    ) -> Optional[str]:
        """Invokes lightweight non-thinking rewriter LLM with strict timeout and zero WS stream leakage."""
        rewriter_llm = get_rewriter_llm(timeout_sec=timeout_sec)
        if rewriter_llm is None:
            return None

        async_client = getattr(rewriter_llm, "http_async_client", None)
        try:
            response = await asyncio.wait_for(
                rewriter_llm.ainvoke(
                    prompt_messages,
                    config={"callbacks": [], "tags": ["internal_rewriter"]},
                ),
                timeout=timeout_sec,
            )
            content = response.content if hasattr(response, "content") else response
            return content if isinstance(content, str) else str(content)
        except asyncio.TimeoutError:
            logger.warning(
                "[QueryRewriter] Lightweight LLM rewriter timed out after %.2fs; falling back to deterministic engine.",
                timeout_sec,
            )
            return None
        except Exception as exc:
            logger.debug(
                "[QueryRewriter] Lightweight LLM rewriter unavailable (%s); falling back to deterministic engine.",
                exc,
            )
            return None
        finally:
            if async_client is not None and hasattr(async_client, "aclose"):
                try:
                    await async_client.aclose()
                except Exception:
                    pass

    async def arewrite(
        self,
        query: str,
        history: Optional[List[BaseMessage]] = None,
        data_source: Optional[str] = None,
    ) -> RewrittenQuery:
        """Executes hybrid async query rewriting: Rule pre-processing -> Optional Non-Thinking LLM -> Deterministic Fallback."""
        # Stage 1 & 3 baseline: always compute fast deterministic rewrite first (0ms)
        det_result = self.rewrite(query=query, history=history)
        recent_history = _extract_recent_history(history, max_turns=MAX_HISTORY_TURNS)

        if not self._should_use_llm(query, recent_history, det_result):
            return det_result

        timeout_sec = max(0.05, float(getattr(settings, "QUERY_REWRITER_LLM_TIMEOUT", 2.5)))
        prompt_messages = self._build_llm_messages(
            query=query,
            recent_history=recent_history,
            data_source=data_source,
        )
        raw_output = await self._invoke_rewriter_llm(prompt_messages, timeout_sec=timeout_sec)
        if not raw_output:
            return det_result

        parsed = _parse_llm_rewriter_json(raw_output)
        if not parsed:
            logger.debug("[QueryRewriter] Invalid LLM rewriter JSON; using deterministic result.")
            return det_result

        standalone_q = parsed["standalone_query"]

        # Coreference quality guard: reject LLM rewrite if it left bare pronouns unresolved when deterministic solved them
        bare_pronouns = ("它", "那个", "那台", "这台", "该设备", "该制度")
        if (
            det_result.coreference_resolved
            and any(p in standalone_q for p in bare_pronouns)
            and not any(p in det_result.standalone_query for p in bare_pronouns)
        ):
            logger.debug("[QueryRewriter] LLM left pronoun unresolved; falling back to deterministic rewrite.")
            return det_result

        # Safety guardrail: prevent situational "出差" from hallucinating FINANCE on pure IT borrowing queries
        llm_domains: List[str] = list(parsed["domains"])
        det_domains, det_weights = self._score_domains(standalone_q)
        if (
            "FINANCE" in llm_domains
            and "FINANCE" not in det_domains
            and "IT" in det_domains
            and not any(k in standalone_q for k in ("报销", "住宿", "酒店", "机票", "高铁", "补贴", "餐补", "发票"))
        ):
            llm_domains = [d for d in llm_domains if d != "FINANCE"]

        # Merge LLM domains with deterministic signal while preserving ranked soft weights
        merged_domains = _dedupe_preserve_order(llm_domains + det_domains)
        merged_weights: Dict[str, float] = {}
        for idx, dom in enumerate(merged_domains):
            if dom in det_weights:
                merged_weights[dom] = det_weights[dom]
            else:
                merged_weights[dom] = round(max(0.55, 1.0 - idx * 0.15), 4)
        # Normalize top domain weight to 1.0 when non-empty
        if merged_weights:
            top_w = max(merged_weights.values())
            if top_w > 0:
                merged_weights = {d: round(min(1.0, w / top_w), 4) for d, w in merged_weights.items()}
            merged_domains = sorted(merged_weights.keys(), key=lambda d: merged_weights[d], reverse=True)

        primary_domain = merged_domains[0] if merged_domains else None

        # Combine LLM sub-queries with deterministic safety fallback (filter out contaminated "出差报销" if FINANCE dropped)
        llm_subs = [
            sq for sq in parsed["sub_queries"]
            if not ("FINANCE" not in merged_domains and "出差报销" in sq)
        ]
        if not llm_subs:
            llm_subs = self._split_sub_queries(standalone_q, primary_domain, domains=merged_domains)
        sub_queries = _dedupe_preserve_order(llm_subs)[:MAX_SUB_QUERIES]

        entities = _dedupe_preserve_order(parsed["entities"] + _extract_entities_from_text(standalone_q))[:10]
        coref_resolved = bool(recent_history and (parsed["coreference_resolved"] or det_result.coreference_resolved))

        logger.info(
            "[QueryRewriter] Hybrid LLM rewrite: '%s' -> '%s' | Domains=%s | Sub-queries=%s",
            query,
            standalone_q,
            merged_domains,
            sub_queries,
        )

        return RewrittenQuery(
            original_query=query,
            standalone_query=standalone_q,
            sub_queries=sub_queries,
            primary_domain=primary_domain,
            extracted_entities=entities,
            domains=merged_domains,
            domain_weights=merged_weights,
            rewrite_method="llm",
            coreference_resolved=coref_resolved,
            anchor_topic=det_result.anchor_topic or (entities[0] if entities else None),
        )


# Global singleton
_global_query_rewriter: Optional[QueryRewriter] = None


def get_query_rewriter() -> QueryRewriter:
    """Returns singleton instance of QueryRewriter."""
    global _global_query_rewriter
    if _global_query_rewriter is None:
        _global_query_rewriter = QueryRewriter()
    return _global_query_rewriter
