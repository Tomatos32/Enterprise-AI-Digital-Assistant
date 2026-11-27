"""Hybrid Cognitive Intent Router Node for LangGraph State Machine.

Implements a 3-tier multi-turn context-aware routing engine:
  - Tier 0: Explicit state/metadata overrides and structured AIMessage tool_calls
  - Tier 1: Deterministic 0ms guardrails (/slash commands, @data_source directives,
            pure chitchat, unambiguous SOP inquiries, operational actions & compound plans)
  - Tier 2: Lightweight non-thinking LLM contextual classifier consuming up to 6 turns
            of conversation history with strict timeout, callback isolation & safety guards
  - Tier 3: Enhanced multi-turn deterministic contextual fallback engine (offline / timeout)
"""

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from backend.core.config import settings
from backend.core.llm import get_router_llm
from backend.graph.state import AgentState
from backend.tools.slot_extractor import (
    APPROVAL_THRESHOLD_RMB,
    detect_pending_clarification_context,
    merge_purchase_amounts_across_turns,
    parse_purchase_amount,
)

logger = logging.getLogger(__name__)

VALID_INTENTS = ("retrieve", "tool", "approval", "chat")
VALID_SECONDARY_INTENTS = ("", "tool", "approval")
VALID_TOOL_HINTS = (
    "query_employee",
    "query_inventory",
    "create_ticket",
    "create_purchase",
    "send_email",
    "search_knowledge_base",
)

MAX_CONTEXT_TURNS = 6
MAX_CONTEXT_MESSAGES = MAX_CONTEXT_TURNS * 2

# ---------------------------------------------------------------------------
# Lexical & Domain Dictionaries
# ---------------------------------------------------------------------------

GREETING_WORDS = {
    "你好", "您好", "hi", "hello", "hey", "早上好", "中午好", "下午好", "晚上好",
    "在吗", "在不在", "哈喽", "嗨", "您好啊", "你好呀", "早安", "晚安",
    "很高兴见到你", "认识你很高兴", "初次见面", "幸会", "辛苦了", "请多关照",
}

ACK_WORDS = {
    "谢谢", "感谢", "多谢", "好的", "收到", "明白", "行", "可以的",
    "ok", "okay", "thanks", "thankyou", "再见", "拜拜", "bye", "嗯", "好的谢谢",
    "明白了", "了解了", "多谢了", "谢谢你", "感谢解答",
}

IDENTITY_WORDS = {
    "你是谁", "介绍一下你自己", "介绍一下自己", "自我介绍", "你能做什么",
    "帮助", "help", "功能介绍", "你的名字", "你会做什么", "你可以帮我做什么",
}

GENERAL_CHAT_UTILITY_PATTERNS = (
    "翻译成", "翻译一下", "帮我翻译", "英译中", "中译英",
    "润色一下", "帮我润色", "改写这段", "总结下面这段", "帮我总结这段",
    "写一首诗", "讲个笑话", "讲一个笑话", "讲个故事", "陪我聊聊", "聊两句",
    "随便聊", "今天天气", "心情不错", "起个名字",
    "写一个快速排序", "写一段代码", "用python写", "用java写", "用js写",
    "算法题", "leetcode",
)

# Policy / SOP inquiry markers (asking about rules rather than executing actions)
SOP_STRONG_NOUNS = (
    "sop", "图文版", "规章", "制度", "规定", "政策", "手册", "细则", "指南",
    "条款", "规范", "红线", "权限矩阵", "管理办法", "门禁", "合规", "上限", "限额",
)

POLICY_INQUIRY_PHRASES = (
    "怎么审批", "如何审批", "审批流程", "审批标准", "审批权限", "谁来审批",
    "需要谁审批", "需要谁签字", "需要谁批", "要谁批", "走什么流程", "什么流程",
    "怎么申请", "如何申请", "怎么报销", "如何报销", "怎么办理", "如何办理",
    "怎么借", "期限是多久", "最长多久", "能借几天", "最多几天", "有几天",
    "扣钱吗", "怎么算", "怎么处罚", "会怎样", "怎么办", "怎么分级",
    "响应sla", "sla是多久", "sla标准", "响应时间", "解决时间",
    "需要押金吗", "要押金吗", "可以报销吗", "能报多少", "多少钱上限",
    "住宿标准", "差旅标准", "报销标准", "有何规定", "有什么规定",
    "是否允许", "是否可以", "能否", "可否", "能不能", "可以吗",
    "查询制度", "查制度", "检索制度", "制度标准", "最新标准",
)

# Operational action verbs (intent to perform an operation vs read policy)
ACTION_SUBMIT_VERBS = (
    "提交", "发起", "申请", "申购", "下单", "帮我买", "我要买", "需要采购",
    "购买", "采购", "走审批", "提个审批", "发起审批", "提交审批",
)

TICKET_EXPLICIT_PHRASES = (
    "创建工单", "新建工单", "提工单", "提个工单", "提一个工单", "提一个报修",
    "提交工单", "开个工单", "建个工单", "拉个工单", "拉个单子", "报修", "报障",
    "create_ticket", "加急开通",
)

INCIDENT_SYMPTOM_WORDS = (
    "蓝屏", "宕机", "打满", "断网", "连不上", "崩溃", "挂了", "坏了",
    "开不了机", "无法登录", "卡死", "cpu打满", "故障排查", "网络中断", "黑屏",
)

EMAIL_ACTION_PHRASES = (
    "发邮件", "发送邮件", "发封邮件", "发个邮件", "发一封邮件", "写封邮件",
    "邮件通知", "发邮件通知", "转发给", "send_email",
)

APPROVAL_EXPLICIT_PHRASES = (
    "发起审批", "人机协同", "大额采购", "会签", "需主管审批",
    "提交审批", "申请大额", "审批单", "提交大额采购", "走大额审批",
)

INVENTORY_ITEM_WORDS = (
    "macbook", "thinkpad", "显示器", "电脑", "笔记本", "备用机", "键盘",
    "鼠标", "办公椅", "服务器", "备件", "耳机", "扩展坞", "ipad", "打印机",
)

INVENTORY_STOCK_PHRASES = (
    "库存", "inventory", "余量", "现货", "备货", "还有几台", "还有多少",
    "剩几台", "剩多少", "有没有货", "有货吗", "可以领", "能领几台", "可领用",
    "仓库", "库里", "还有吗", "剩几个", "还有几个",
)

EMPLOYEE_CONTACT_ATTRS = (
    "电话", "手机", "手机号", "联系方式", "邮箱", "email", "工号",
    "职级", "岗位", "所属部门", "哪个部门", "分机", "是谁", "信息",
)

# Common Chinese surnames for natural person-name recognition (e.g. "张伟的电话")
_COMMON_SURNAMES = (
    "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜"
    "戚谢邹喻柏水窦章云苏潘葛奚范彭郎鲁韦昌马苗凤花方俞任袁柳酆鲍史唐"
    "费廉岑薛雷贺倪汤滕殷罗毕郝邬安常乐于时傅皮卞齐康伍余元卜顾孟平黄"
    "穆萧尹姚邵湛汪祁毛禹狄米贝明臧计伏成戴谈宋茅庞熊纪舒屈项祝董梁杜"
    "阮蓝闵席季麻强贾路娄危江童颜郭梅盛林刁钟徐邱骆高夏蔡田樊胡凌霍"
)
_PERSON_NAME_ATTR_RE = re.compile(
    rf"(?:[{_COMMON_SURNAMES}][一-龥]{{1,2}}|\{{\{{PERSON_[a-zA-Z0-9_]+\}}\}})"
    r"(?:的|在|是|老师|同事|经理|主管|总)?(?:电话|手机|手机号|联系方式|邮箱|email|工号|职级|岗位|部门|哪个部门|分机|信息)",
    re.IGNORECASE,
)

# Non-person domain nouns that happen to start with a common surname character
_NON_PERSON_PREFIXES = (
    "高管", "高铁", "高配", "高危", "高温", "高度",
    "常驻", "常规", "常见", "日常",
    "明文", "明细", "明确", "明年", "明天",
    "平安", "平台", "平均", "平日",
    "金蝶", "金额", "金融",
    "华东", "华南", "华北", "华为",
    "市场", "市值",
    "方法", "方案", "方式",
    "白云", "白名单",
    "主机", "主管", "主题", "主动",
    "财务", "财产",
    "人员", "人事", "人力", "人机",
    "公司", "公积", "公开", "办公",
    "安全", "安装", "安排",
    "费用", "费率",
    "标准", "保密", "报销",
    "客户", "客服",
    "开发", "开源", "开机",
    "系统", "硬件", "软件", "网络", "数据", "设备", "资产", "文档", "制度", "流程",
)

ENTERPRISE_KNOWLEDGE_KEYWORDS = (
    # SOP & Guidelines
    "sop", "图文版", "规定", "文档", "政策", "手册", "规章", "指南", "制度", "流程",
    "标准", "规范", "细则", "条款", "合规", "管理办法", "门禁",
    # IT & Workstation & Asset SLA (03_IT)
    "备用机", "借用", "借机", "归还", "外借", "电脑", "笔记本", "macbook", "thinkpad",
    "显示器", "外设", "资产", "设备", "折旧", "换新", "硬件", "配置", "vpn", "ztna",
    "密码", "mfa", "权限", "开源协议", "开源代码", "商用", "密钥", "服务器", "集群",
    "故障", "sla", "p0", "p1", "p2", "p3", "p4", "响应时间", "解决时间", "押金",
    # Procurement & Purchasing (02_PROCUREMENT)
    "采购", "供应商", "询价", "招标", "验收", "领用", "固定资产", "审批", "签字",
    # HR, Attendance & Welfare (01_HR)
    "人事", "考勤", "打卡", "请假", "年假", "事假", "病假", "产假", "育儿假", "婚假", "丧假",
    "迟到", "早退", "旷工", "加班", "调休", "社保", "公积金", "薪酬", "工资", "调薪",
    "绩效", "年终奖", "离职", "交接", "试用期", "转正", "福利", "招聘", "录用", "入职", "实习生",
    # Finance & Travel (04_FINANCE)
    "财务", "报销", "出差", "差旅", "住宿", "酒店", "机票", "高铁", "交通补贴", "餐补",
    "借款", "发票", "税号", "预算", "额度", "单价", "超额", "一线城市", "二线城市", "三线城市",
    # Security & Compliance (05_SECURITY)
    "安全", "保密", "泄密", "数据安全", "知识产权", "禁令", "脱敏", "审计", "红线",
    # CS (06_CS)
    "售后", "投诉", "退换货", "回访", "客户服务", "工单分级",
)

AUDIT_READ_ONLY_KEYWORDS = (
    "查看", "检查", "列出", "待审", "待审批", "列表", "进度", "面板", "状态",
    "有哪些", "审批中心", "待办", "看看", "查一下", "查询",
)

COMPOUND_CONNECTORS = ("并且", "并", "然后", "再", "顺便", "同时", "接着")

FOLLOW_UP_MARKERS = (
    "那", "呢", "如果", "要是", "超过", "不满", "逾期", "再", "顺便",
    "他", "她", "它", "这个", "那个", "上述", "前述", "此项", "该",
    "二线", "三线", "产假", "病假", "事假", "押金", "发票", "总监", "签字",
    "提交一个", "提一个", "发起吧", "申请吧", "下单吧", "报修吧", "还有吗", "还有别的",
)

# ---------------------------------------------------------------------------
# Pure Guard & Helper Functions
# (Chinese/Arabic numeral & purchase amount parser shared from backend.tools.slot_extractor)
# ---------------------------------------------------------------------------


def _is_pure_chitchat(query: str) -> bool:
    """Detects whether user query is purely a conversational greeting, acknowledgement, or identity question."""
    cleaned = re.sub(r"[^\w一-鿿]", "", query.lower()).strip()
    if not cleaned:
        return True
    if cleaned in GREETING_WORDS or cleaned in ACK_WORDS or cleaned in IDENTITY_WORDS:
        return True

    remainder = cleaned
    for g in sorted(GREETING_WORDS, key=len, reverse=True):
        if remainder.startswith(g):
            remainder = remainder[len(g):].strip()
    if not remainder or remainder in GREETING_WORDS or remainder in ACK_WORDS or remainder in IDENTITY_WORDS:
        return True

    if any(
        id_word in cleaned
        for id_word in ("你是谁", "介绍一下自己", "介绍一下你自己", "自我介绍", "你能做什么", "你的名字", "功能介绍", "你可以帮我做什么")
    ):
        if not any(
            domain_w in cleaned
            for domain_w in ("制度", "规章", "报销", "借用", "出差", "采购", "工单", "配置", "标准", "库存", "员工")
        ):
            return True
    return False


def _is_general_chat_utility(q_lower: str) -> bool:
    """Detects general language/coding/chitchat utility prompts unrelated to enterprise SOPs or tools."""
    if not any(pat in q_lower for pat in GENERAL_CHAT_UTILITY_PATTERNS):
        return False
    # If the user explicitly asks to translate/summarize an enterprise SOP or submit a tool action, do not intercept
    if any(kw in q_lower for kw in ("制度", "规章", "sop", "报销标准", "审批流程", "创建工单", "发邮件", "查库存")):
        return False
    return True


def _is_policy_inquiry(q_lower: str) -> bool:
    """Distinguishes asking about company policies/rules from requesting operational execution."""
    has_sop_noun = any(w in q_lower for w in SOP_STRONG_NOUNS)
    has_inquiry_phrase = any(w in q_lower for w in POLICY_INQUIRY_PHRASES)
    if has_sop_noun or has_inquiry_phrase:
        return True
    # Question form about approval / SLA / leave / reimbursement rules
    if ("审批" in q_lower or "sla" in q_lower or "工单" in q_lower) and any(
        q_w in q_lower for q_w in ("怎么", "如何", "谁来", "需要谁", "多久", "多少", "什么条件", "什么标准", "是什么")
    ):
        return True
    return False


def _has_explicit_action_submission(q_lower: str) -> bool:
    """Checks whether the user is asking to execute/submit an approval or operational action."""
    if any(p in q_lower for p in APPROVAL_EXPLICIT_PHRASES):
        return True
    if any(p in q_lower for p in TICKET_EXPLICIT_PHRASES):
        return True
    if any(p in q_lower for p in EMAIL_ACTION_PHRASES):
        return True
    if any(v in q_lower for v in ("提交", "发起", "下单", "申购", "帮我买", "我要买", "帮我采购", "申请采购", "申请购买")):
        return True
    return False


def _parse_slash_command(query: str, metadata: Dict[str, Any]) -> Tuple[Optional[str], str]:
    """Parses leading slash command (/kb, /audit, /help, /ticket, /search) and returns (cmd, clean_query)."""
    stripped = query.strip()
    meta_cmd = str(metadata.get("slash_command") or "").strip().lower().lstrip("/")

    match = re.match(r"^/([a-zA-Z]+)(?:\s+(.*))?$", stripped, flags=re.DOTALL)
    if match:
        cmd = match.group(1).lower()
        rest = (match.group(2) or "").strip()
        return cmd, rest

    if meta_cmd in ("kb", "audit", "help", "ticket", "search", "rag"):
        return meta_cmd, stripped

    return None, stripped


def _extract_data_source(query: str, metadata: Dict[str, Any]) -> Tuple[Optional[str], str]:
    """Resolves @data_source from metadata or inline '@...' tag and returns (source_key, clean_query)."""
    source_id = str(metadata.get("data_source_id") or "").strip().lower()
    source_name = str(metadata.get("data_source") or metadata.get("attached_source") or "").strip()
    cleaned_query = query.strip()

    # Also detect inline @Source prefix when typed directly without clicking popover
    if not source_id and not source_name:
        inline_match = re.match(
            r"^@(全量企业规章制度库|MySQL\s*业务台账|ERP\s*采购与供应链|HR制度库|财务报销标准|IT运维规范|采购管理办法|[\w一-鿿.-]+)(?:\s+(.*))?$",
            cleaned_query,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if inline_match:
            source_name = inline_match.group(1).strip()
            cleaned_query = (inline_match.group(2) or "").strip() or cleaned_query

    combined = f"{source_id} {source_name}".lower().strip()
    if not combined:
        return None, cleaned_query

    if "db_mysql" in combined or "mysql" in combined or "业务台账" in combined:
        return "db_mysql", cleaned_query
    if "erp_sap" in combined or "erp" in combined or "sap" in combined or "供应链" in combined:
        return "erp_sap", cleaned_query
    if (
        "kb_all" in combined
        or "规章制度" in combined
        or "制度库" in combined
        or "知识库" in combined
        or any(ext in combined for ext in (".md", ".pdf", ".xlsx", ".csv", ".txt", ".docx"))
        or any(tag in combined for tag in ("hr", "财务", "it运维", "采购管理", "安全"))
    ):
        return "kb_all", cleaned_query

    # Unknown custom attached source defaults to knowledge retrieval
    return "kb_all", cleaned_query


def _detect_tool_intent(q_lower: str, query: str) -> Tuple[bool, Optional[str], bool]:
    """Detects operational tool intent and returns (matched, tool_hint, high_confidence)."""
    is_policy = _is_policy_inquiry(q_lower)

    # 1. Explicit generic tool call command
    if any(kw in q_lower for kw in ("调用工具", "执行工具", "execute_tool")):
        return True, None, True

    # 2. Ticket creation / incident reporting
    if any(kw in q_lower for kw in TICKET_EXPLICIT_PHRASES):
        if not (is_policy and not any(v in q_lower for v in ("帮我", "请", "创建", "新建", "提交", "提个", "提一个", "开个", "拉个", "报修"))):
            return True, "create_ticket", True

    if not is_policy and any(sym in q_lower for sym in INCIDENT_SYMPTOM_WORDS):
        if any(act in q_lower for act in ("帮我", "处理", "排查", "修", "报", "工单", "加急", "赶紧", "联系运维", "解决")):
            return True, "create_ticket", False

    # 3. Email sending
    if any(kw in q_lower for kw in EMAIL_ACTION_PHRASES):
        if not (is_policy and "规范" in q_lower):
            return True, "send_email", True
    if not is_policy and re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", query) and any(
        w in q_lower for w in ("发", "转发", "通知", "抄送", "邮件")
    ):
        return True, "send_email", True

    # 4. Employee query (explicit or natural person + contact/profile attribute)
    has_emp_word = any(w in q_lower for w in ("员工", "employee", "同事"))
    has_emp_attr = any(attr in q_lower for attr in EMPLOYEE_CONTACT_ATTRS)
    if has_emp_word and (has_emp_attr or any(v in q_lower for v in ("查", "找", "看看"))):
        if not is_policy:
            return True, "query_employee", True

    if not is_policy:
        person_match = _PERSON_NAME_ATTR_RE.search(query)
        if person_match:
            matched_text = person_match.group(0)
            if not any(matched_text.startswith(np) for np in _NON_PERSON_PREFIXES):
                return True, "query_employee", False

    # 5. Inventory lookup (explicit or natural item + stock availability)
    has_stock_word = any(w in q_lower for w in ("库存", "inventory", "余量", "现货", "备货"))
    if has_stock_word and not is_policy:
        return True, "query_inventory", True

    has_item = any(item in q_lower for item in INVENTORY_ITEM_WORDS)
    has_avail = any(p in q_lower for p in INVENTORY_STOCK_PHRASES)
    if has_item and has_avail and not is_policy:
        # Exclude pure borrowing duration/rule questions ("借用备用机期限是多久")
        if not any(w in q_lower for w in ("借用", "借机", "期限", "多久", "几天", "归还")):
            return True, "query_inventory", False

    return False, None, False


def _detect_approval_intent(q_lower: str, query: str, amount: Optional[float]) -> Tuple[bool, bool]:
    """Detects high-value purchase or explicit approval submission. Returns (matched, high_confidence)."""
    is_policy = _is_policy_inquiry(q_lower)

    # Explicit approval trigger phrases (e.g. "发起审批", "提交大额采购", "申请大额设备采购")
    if any(kw in q_lower for kw in APPROVAL_EXPLICIT_PHRASES):
        if is_policy and not any(v in q_lower for v in ("申请", "提交", "发起", "走审批", "帮我")):
            return False, False
        return True, True

    # Dynamic amount-based purchase approval (> 5,000 RMB) when requesting action (not policy inquiry)
    has_purchase_action = any(
        w in q_lower for w in ("采购", "购买", "申购", "帮我买", "我要买", "买一台", "买两台", "买几台", "下单")
    ) or bool(re.search(r"买\s*(?:\d+|[一二两三四五六七八九十]+)\s*(?:台|个|件|套|把|张|部)", q_lower))

    if has_purchase_action and not is_policy:
        if amount is not None and amount > APPROVAL_THRESHOLD_RMB:
            return True, True
        if any(w in q_lower for w in ("大额", "超额")):
            return True, True

    return False, False


def _detect_purchase_without_amount(q_lower: str) -> bool:
    """Detects explicit procurement submission requests that omit price/budget."""
    if _is_policy_inquiry(q_lower):
        return False
    explicit_phrases = (
        "申请采购",
        "帮我采购",
        "我要采购",
        "我想采购",
        "需要采购",
        "申购",
        "下单采购",
        "提交采购",
        "发起采购",
        "帮我买",
        "我要买",
        "我想买",
        "申请购买",
        "帮我购买",
        "我要购买",
    )
    if any(p in q_lower for p in explicit_phrases):
        return True
    if re.search(r"(?:采购|购买|买)\s*(?:\d+|[一二两三四五六七八九十]+)\s*(?:台|个|件|套|把|张|部|批|只|箱)", q_lower):
        return True
    return False


def _detect_compound_intent(q_lower: str, query: str, amount: Optional[float]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Detects compound two-step requests: policy check (retrieve) + action (tool or approval).

    Example: "请帮我核对研发部 MacBook Pro 采购申请的最新制度标准，并提交审批。"
             "先查一下IT运维部备用机借用标准，再帮我查一下MacBook库存"
    Returns (primary_intent, secondary_intent, tool_hint) or (None, None, None).
    """
    has_connector = any(c in q_lower for c in COMPOUND_CONNECTORS)
    if not has_connector:
        return None, None, None

    has_policy_part = any(
        w in q_lower
        for w in ("制度", "标准", "规章", "规范", "政策", "sop", "细则", "条款", "核对", "sla")
    )
    if not has_policy_part:
        return None, None, None

    # Compound: retrieve -> approval
    has_approval_second = any(
        p in q_lower
        for p in ("提交审批", "发起审批", "并审批", "申请审批", "走审批", "提交大额", "并提交申请")
    ) or (
        amount is not None
        and amount > APPROVAL_THRESHOLD_RMB
        and any(v in q_lower for v in ("提交", "发起", "申请采购", "下单"))
    )
    if has_approval_second:
        return "retrieve", "approval", None

    # Compound: retrieve -> tool
    tool_matched, tool_hint, _ = _detect_tool_intent(q_lower, query)
    # Also check explicit second-clause tool verbs even if first clause triggered _is_policy_inquiry
    if not tool_matched:
        if any(kw in q_lower for kw in TICKET_EXPLICIT_PHRASES):
            tool_matched, tool_hint = True, "create_ticket"
        elif any(kw in q_lower for kw in EMAIL_ACTION_PHRASES):
            tool_matched, tool_hint = True, "send_email"
        elif any(kw in q_lower for kw in ("查库存", "查一下库存", "查下库存", "查询库存", "看看库存")) or (
            any(item in q_lower for item in INVENTORY_ITEM_WORDS) and "库存" in q_lower
        ):
            tool_matched, tool_hint = True, "query_inventory"
        elif any(kw in q_lower for kw in ("查员工", "查一下他的", "联系方式")):
            tool_matched, tool_hint = True, "query_employee"

    if tool_matched and tool_hint:
        return "retrieve", "tool", tool_hint

    return None, None, None


# ---------------------------------------------------------------------------
# Multi-Turn Context Extraction & Deterministic Continuation (Last 6 Turns)
# ---------------------------------------------------------------------------


def _extract_recent_history(messages: Sequence[BaseMessage], max_turns: int = MAX_CONTEXT_TURNS) -> List[Tuple[str, str]]:
    """Extracts up to max_turns*2 recent prior messages (excluding current turn) as (role, text)."""
    if len(messages) <= 1:
        return []

    prior = list(messages[:-1])
    deduped: List[Tuple[str, str]] = []
    for msg in prior:
        if isinstance(msg, HumanMessage):
            role = "user"
        elif isinstance(msg, AIMessage):
            role = "assistant"
        else:
            continue
        text = str(getattr(msg, "content", "")).strip()
        if not text:
            continue
        # Deduplicate consecutive identical entries (e.g., MemorySaver + DB reload overlap)
        if deduped and deduped[-1] == (role, text[:220]):
            continue
        deduped.append((role, text[:220]))

    return deduped[-(max_turns * 2):]


def _infer_multi_turn_intent(
    query: str,
    q_lower: str,
    history: List[Tuple[str, str]],
) -> Tuple[Optional[str], Optional[str], str]:
    """Resolves elliptical / anaphoric follow-ups using the recent 6-turn conversation window.

    Returns (intent, tool_hint, reason) or (None, None, "").
    """
    if not history:
        return None, None, ""

    is_short_or_followup = len(query) <= 32 or any(m in q_lower for m in FOLLOW_UP_MARKERS)
    if not is_short_or_followup:
        return None, None, ""

    recent_text = "\n".join(text for _, text in history[-6:])
    recent_lower = recent_text.lower()

    # 1. Follow-up intent shift to Approval ("那帮我提交一个吧" / "那就申请吧" / "提交审批吧")
    if any(
        p in q_lower
        for p in ("提交一个", "提一个吧", "提交吧", "帮我提交", "那就申请", "帮我申请", "发起审批", "提交审批", "下单吧")
    ):
        # If prior context was about incident/ticket/repair -> shift to create_ticket tool
        if any(w in recent_lower for w in ("工单", "报修", "故障", "sla", "蓝屏", "宕机", "运维")) and not any(
            w in recent_lower for w in ("采购", "购买", "macbook", "审批单", "大额")
        ):
            return "tool", "create_ticket", "multi_turn_shift_to_ticket"

        # If prior context discussed purchase/equipment/approval -> shift to approval (or small purchase tool)
        if any(w in recent_lower for w in ("采购", "购买", "审批", "macbook", "电脑", "笔记本", "服务器", "显示器", "预算")):
            prior_amount = parse_purchase_amount(recent_text)
            if prior_amount is not None and prior_amount <= APPROVAL_THRESHOLD_RMB and "审批" not in q_lower:
                return "tool", "create_purchase", "multi_turn_shift_to_small_purchase"
            return "approval", None, "multi_turn_shift_to_approval"

    # 2. Follow-up employee pronoun query ("再查一下他的邮箱", "他电话多少", "她的部门呢")
    if any(p in q_lower for p in ("他", "她", "这位", "这个人")) and any(
        attr in q_lower for attr in EMPLOYEE_CONTACT_ATTRS
    ):
        if (
            any(w in recent_lower for w in ("员工", "职级", "岗位", "部门", "联系方式", "邮箱", "电话"))
            or _PERSON_NAME_ATTR_RE.search(recent_text) is not None
        ):
            return "tool", "query_employee", "multi_turn_employee_coref"

    # 3. Follow-up inventory check ("那显示器呢", "ThinkPad还有吗", "再查一下余量")
    if any(w in recent_lower for w in ("库存", "余量", "还有几台", "现货", "query_inventory")):
        if any(item in q_lower for item in INVENTORY_ITEM_WORDS) or any(
            p in q_lower for p in ("呢", "还有吗", "剩多少", "库存", "余量")
        ):
            if not _is_policy_inquiry(q_lower):
                return "tool", "query_inventory", "multi_turn_inventory_followup"

    # 4. Follow-up RAG policy continuation ("如果超过这个天数呢", "那产假呢", "二线城市呢", "需要押金吗")
    prior_was_policy = (
        "[rag answer]" in recent_lower
        or "依据制度" in recent_lower
        or any(kw in recent_lower for kw in ENTERPRISE_KNOWLEDGE_KEYWORDS)
    )
    if prior_was_policy:
        is_question_continuation = (
            q_lower.endswith(("?", "？", "呢", "吗"))
            or any(
                m in q_lower
                for m in (
                    "超过", "不满", "逾期", "如果", "要是", "那", "需要", "怎么", "如何",
                    "多少", "几天", "多久", "二线", "三线", "一线", "押金", "发票", "签字",
                    "处罚", "还有", "别的", "规定", "标准", "限额", "条件",
                )
            )
        )
        if is_question_continuation and not _is_general_chat_utility(q_lower):
            return "retrieve", None, "multi_turn_policy_continuation"

    return None, None, ""


# ---------------------------------------------------------------------------
# Tier 2: Lightweight Non-Thinking LLM Contextual Classifier
# ---------------------------------------------------------------------------

_ROUTER_SYSTEM_PROMPT = """你是企业级 AI 助手的意图路由器。请根据最近对话历史和当前用户输入，输出唯一合法的 JSON 对象（禁止输出任何解释或 Markdown 之外的内容）。

可选主意图 (intent):
- "retrieve": 查询企业规章制度、SOP流程、审批权限规定、报销/差旅/休假/考勤/借用/安全/SLA标准、制度追问（如"采购超过5万需要谁审批？"、"P1工单SLA多久？"、"如果超过这个天数呢？"）。
- "tool": 执行实时业务查询或操作——查员工电话/邮箱/部门/职级(query_employee)、查设备库存/余量(query_inventory)、创建报修/运维工单(create_ticket)、发送邮件(send_email)、提交<=5000元小额采购(create_purchase)。
- "approval": 发起或提交大额采购审批（总金额>5000元）或明确要求发起人机协同审批申请（如"帮我买2台3500元显示器"、"那帮我提交一个吧"承接前文采购）。注意：仅询问审批规定/流程属于 "retrieve"，不是 "approval"。
- "chat": 寒暄问候、闲聊、翻译、文本润色/摘要、编程问答等与企业制度和业务操作无关的通用对话。

可选次级意图 (secondary_intent):
- 仅当用户在同一句话明确要求"先查制度/核对标准，再执行工具或提交审批"时，设 intent="retrieve"，secondary_intent="tool" 或 "approval"；否则为 null。

输出严格 JSON 格式:
{"intent":"retrieve|tool|approval|chat","secondary_intent":null,"tool_hint":null,"confidence":0.9,"reason":"简短理由"}"""


def _build_llm_router_messages(
    query: str,
    history: List[Tuple[str, str]],
    data_source: Optional[str] = None,
) -> List[BaseMessage]:
    """Constructs compact prompt messages with up to 6 turns of history for fast LLM classification."""
    lines: List[str] = []
    if history:
        lines.append("【最近对话上下文】")
        for role, text in history[-MAX_CONTEXT_MESSAGES:]:
            role_label = "用户" if role == "user" else "助手"
            lines.append(f"{role_label}: {text}")
    if data_source:
        lines.append(f"【关联数据源】: {data_source}")
    lines.append(f"【当前用户输入】: {query}")

    return [
        SystemMessage(content=_ROUTER_SYSTEM_PROMPT),
        HumanMessage(content="\n".join(lines)),
    ]


def _parse_llm_router_json(raw_text: str) -> Optional[Dict[str, Any]]:
    """Robustly extracts and validates JSON classification payload from LLM text."""
    if not raw_text or not isinstance(raw_text, str):
        return None

    # Strip <think>...</think> blocks if any reasoning model ignores think=False
    cleaned = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL | re.IGNORECASE).strip()
    # Strip markdown code fences
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, flags=re.DOTALL)
    if fence_match:
        json_candidate = fence_match.group(1)
    else:
        brace_match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not brace_match:
            return None
        json_candidate = brace_match.group(0)

    try:
        parsed = json.loads(json_candidate)
    except json.JSONDecodeError:
        return None

    if not isinstance(parsed, dict):
        return None

    intent = str(parsed.get("intent") or "").strip().lower()
    if intent not in VALID_INTENTS:
        return None

    raw_secondary = parsed.get("secondary_intent")
    secondary_intent = ""
    if raw_secondary is not None:
        sec_str = str(raw_secondary).strip().lower()
        if sec_str in ("tool", "approval") and intent == "retrieve":
            secondary_intent = sec_str

    raw_tool_hint = parsed.get("tool_hint")
    tool_hint: Optional[str] = None
    if raw_tool_hint is not None:
        th = str(raw_tool_hint).strip()
        if th in VALID_TOOL_HINTS:
            tool_hint = th

    try:
        confidence = float(parsed.get("confidence", 0.75))
    except (TypeError, ValueError):
        confidence = 0.75
    confidence = max(0.0, min(1.0, confidence))

    reason = str(parsed.get("reason") or "llm_classified").strip()[:120]

    return {
        "intent": intent,
        "secondary_intent": secondary_intent,
        "tool_hint": tool_hint,
        "confidence": confidence,
        "reason": reason,
    }


async def _invoke_router_llm(
    prompt_messages: List[BaseMessage],
    timeout_sec: float,
) -> Optional[str]:
    """Invokes the lightweight non-thinking router LLM with strict timeout and callback isolation."""
    router_llm = get_router_llm(timeout_sec=timeout_sec)
    if router_llm is None:
        return None

    async_client = getattr(router_llm, "http_async_client", None)
    try:
        # Pass empty callbacks so LangGraph astream_events never streams router JSON tokens to WS
        response = await asyncio.wait_for(
            router_llm.ainvoke(prompt_messages, config={"callbacks": [], "tags": ["internal_router"]}),
            timeout=timeout_sec,
        )
        content = response.content if hasattr(response, "content") else response
        return content if isinstance(content, str) else str(content)
    except asyncio.TimeoutError:
        logger.warning("[RouterNode] Lightweight LLM classifier timed out after %.2fs; falling back to rules.", timeout_sec)
        return None
    except Exception as exc:
        logger.debug("[RouterNode] Lightweight LLM classifier unavailable (%s); falling back to rules.", exc)
        return None
    finally:
        if async_client is not None and hasattr(async_client, "aclose"):
            try:
                await async_client.aclose()
            except Exception:
                pass


async def _classify_with_llm(
    query: str,
    q_lower: str,
    history: List[Tuple[str, str]],
    data_source: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Executes Tier 2 LLM classification and applies deterministic post-validation safety guards."""
    if not getattr(settings, "ROUTER_LLM_ENABLED", True):
        return None

    timeout_sec = max(0.05, float(getattr(settings, "ROUTER_LLM_TIMEOUT", 2.5)))
    prompt_messages = _build_llm_router_messages(query=query, history=history, data_source=data_source)
    raw_output = await _invoke_router_llm(prompt_messages, timeout_sec=timeout_sec)
    if not raw_output:
        return None

    parsed = _parse_llm_router_json(raw_output)
    if not parsed or parsed["confidence"] < 0.55:
        return None

    # Safety Guard: Prevent LLM from misfiring 'approval' (DB write + interrupt) on pure policy questions
    asks_who_or_how_to_approve = any(
        p in q_lower
        for p in ("怎么审批", "如何审批", "审批流程", "需要谁审批", "谁来审批", "需要谁签字", "走什么流程", "什么标准")
    )
    explicit_submit_now = any(
        p in q_lower for p in ("发起审批", "提交审批", "帮我提交", "提交大额", "立刻下单", "马上提交")
    )
    if parsed["intent"] == "approval" and (
        (_is_policy_inquiry(q_lower) and not _has_explicit_action_submission(q_lower))
        or (asks_who_or_how_to_approve and not explicit_submit_now)
    ):
        logger.info("[RouterNode] Safety guard overrode LLM 'approval' -> 'retrieve' for policy inquiry.")
        parsed["intent"] = "retrieve"
        parsed["secondary_intent"] = ""
        parsed["reason"] = "safety_guard_policy_over_approval"

    return parsed


# ---------------------------------------------------------------------------
# Tier 3: Enhanced Multi-Turn Deterministic Fallback Engine
# ---------------------------------------------------------------------------


def _classify_deterministic_fallback(
    query: str,
    q_lower: str,
    history: List[Tuple[str, str]],
    amount: Optional[float],
) -> Tuple[str, str, Optional[str], float, str]:
    """Offline / timeout fallback classifier with full multi-turn, amount & domain disambiguation.

    Returns (intent, secondary_intent, tool_hint, confidence, reason).
    """
    # 1. General chat utility (translation, polishing, coding, small talk)
    if _is_general_chat_utility(q_lower):
        return "chat", "", None, 0.90, "general_chat_utility"

    # 2. Compound intent (retrieve + approval / tool)
    comp_primary, comp_secondary, comp_tool = _detect_compound_intent(q_lower, query, amount)
    if comp_primary and comp_secondary:
        return comp_primary, comp_secondary, comp_tool, 0.90, f"compound_{comp_primary}_{comp_secondary}"

    # 3. Multi-turn follow-up resolution (inheritance or intent shift across 6 turns)
    mt_intent, mt_tool, mt_reason = _infer_multi_turn_intent(query, q_lower, history)
    if mt_intent:
        return mt_intent, "", mt_tool, 0.84, mt_reason

    # 4. Natural tool execution (employee, inventory, ticket, email)
    tool_matched, tool_hint, _ = _detect_tool_intent(q_lower, query)
    if tool_matched:
        return "tool", "", tool_hint, 0.85, f"natural_tool_{tool_hint or 'generic'}"

    # 5. Dynamic purchase amount & approval vs small purchase
    approval_matched, _ = _detect_approval_intent(q_lower, query, amount)
    if approval_matched:
        return "approval", "", None, 0.88, "dynamic_amount_or_approval"

    if (
        amount is not None
        and 0 < amount <= APPROVAL_THRESHOLD_RMB
        and not _is_policy_inquiry(q_lower)
        and any(w in q_lower for w in ("采购", "购买", "申购", "买", "下单"))
    ):
        return "tool", "", "create_purchase", 0.84, "small_purchase_auto_tool"

    if amount is None and _detect_purchase_without_amount(q_lower):
        return "tool", "", "create_purchase", 0.84, "purchase_missing_amount_slot_clarification"

    # 6. Enterprise policy & knowledge retrieval
    if _is_policy_inquiry(q_lower) or any(kw in q_lower for kw in ENTERPRISE_KNOWLEDGE_KEYWORDS):
        return "retrieve", "", None, 0.82, "enterprise_domain_knowledge"

    # 7. Default for non-enterprise conversational queries: chat (removed blind len >= 4 -> retrieve)
    return "chat", "", None, 0.70, "default_general_chat"


# ---------------------------------------------------------------------------
# Main LangGraph Router Node Entrypoint
# ---------------------------------------------------------------------------


def _build_route_result(
    intent: str,
    metadata: Dict[str, Any],
    *,
    secondary_intent: str = "",
    routing_method: str,
    confidence: float,
    reason: str,
    tool_hint: Optional[str] = None,
    normalized_query: Optional[str] = None,
    slash_command: Optional[str] = None,
    data_source_resolved: Optional[str] = None,
    parsed_amount: Optional[float] = None,
    preserve_pending_slots: bool = False,
) -> Dict[str, Any]:
    """Constructs standardized AgentState update returned by router_node."""
    updated_meta = dict(metadata)
    # Clear per-turn execution flags so reused LangGraph threads never inherit stale tool/approval state
    updated_meta.pop("tool_executed", None)
    updated_meta.pop("tool_output", None)
    updated_meta.pop("approval_executed", None)
    updated_meta.pop("approval_result", None)
    updated_meta.pop("slot_clarification_needed", None)
    updated_meta.pop("slot_clarification_question", None)
    updated_meta.pop("missing_slots", None)
    updated_meta.pop("escalate_to_approval", None)
    if not preserve_pending_slots:
        updated_meta.pop("pending_slot_tool", None)
        updated_meta.pop("pending_slots", None)
    updated_meta["routing_method"] = routing_method
    updated_meta["routing_confidence"] = round(confidence, 3)
    updated_meta["routing_reason"] = reason
    if secondary_intent:
        updated_meta["secondary_intent"] = secondary_intent
    else:
        updated_meta.pop("secondary_intent", None)

    if tool_hint:
        updated_meta["tool_hint"] = tool_hint
    else:
        updated_meta.pop("tool_hint", None)

    if normalized_query is not None:
        updated_meta["normalized_query"] = normalized_query
    if slash_command:
        updated_meta["slash_command"] = slash_command
    else:
        updated_meta.pop("slash_command", None)
    if data_source_resolved:
        updated_meta["resolved_data_source"] = data_source_resolved
    else:
        updated_meta.pop("resolved_data_source", None)
    if parsed_amount is not None:
        updated_meta["parsed_purchase_amount"] = parsed_amount
    else:
        updated_meta.pop("parsed_purchase_amount", None)

    return {
        "intent": intent,
        "secondary_intent": secondary_intent,
        "metadata": updated_meta,
        "current_step": "routed",
    }


async def router_node(state: AgentState) -> Dict[str, Any]:
    """Hybrid Cognitive Intent Router Node for LangGraph State Machine.

    Routes execution to 'retrieve', 'tool', 'approval', or 'chat' (with optional
    compound 'secondary_intent' of 'tool' or 'approval' after 'retrieve').
    """
    metadata: Dict[str, Any] = dict(state.get("metadata") or {})

    # ------------------------------------------------------------------
    # Tier 0: Explicit Overrides & Structured AIMessage tool_calls
    # ------------------------------------------------------------------
    explicit_intent = str(state.get("intent") or "").strip().lower()
    if explicit_intent in VALID_INTENTS:
        return _build_route_result(
            explicit_intent,
            metadata,
            secondary_intent=str(state.get("secondary_intent") or ""),
            routing_method="explicit_state_intent",
            confidence=1.0,
            reason="state_intent_override",
        )

    override_intent = str(metadata.get("override_intent") or "").strip().lower()
    if override_intent in VALID_INTENTS:
        return _build_route_result(
            override_intent,
            metadata,
            secondary_intent=str(metadata.get("override_secondary_intent") or ""),
            routing_method="metadata_override",
            confidence=1.0,
            reason="metadata_override_intent",
        )

    messages = list(state.get("messages", []))
    if messages:
        last_msg = messages[-1]
        tool_calls = getattr(last_msg, "tool_calls", None)
        if tool_calls:
            return _build_route_result(
                "tool",
                metadata,
                routing_method="explicit_tool_calls",
                confidence=1.0,
                reason="ai_message_tool_calls",
            )
        raw_query = str(getattr(last_msg, "content", "")).strip()
    else:
        raw_query = ""

    if not raw_query:
        return _build_route_result(
            "chat",
            metadata,
            routing_method="empty_query_guard",
            confidence=1.0,
            reason="empty_input",
        )

    history = _extract_recent_history(messages, max_turns=MAX_CONTEXT_TURNS)

    # ------------------------------------------------------------------
    # Tier 1A: Deterministic /Slash Commands & @DataSource Directives (0ms)
    # ------------------------------------------------------------------
    slash_cmd, after_slash = _parse_slash_command(raw_query, metadata)
    if slash_cmd:
        clean_q = after_slash or raw_query
        clean_lower = clean_q.lower()
        amount = parse_purchase_amount(clean_q)

        if slash_cmd == "help":
            return _build_route_result(
                "chat",
                metadata,
                routing_method="slash_command",
                confidence=1.0,
                reason="slash_help",
                normalized_query=clean_q,
                slash_command="help",
            )

        if slash_cmd in ("kb", "search", "rag"):
            comp_p, comp_s, comp_t = _detect_compound_intent(clean_lower, clean_q, amount)
            return _build_route_result(
                "retrieve",
                metadata,
                secondary_intent=comp_s or "",
                routing_method="slash_command",
                confidence=1.0,
                reason="slash_kb",
                tool_hint=comp_t,
                normalized_query=after_slash or clean_q,
                slash_command="kb",
                parsed_amount=amount,
            )

        if slash_cmd == "ticket":
            return _build_route_result(
                "tool",
                metadata,
                routing_method="slash_command",
                confidence=1.0,
                reason="slash_ticket",
                tool_hint="create_ticket",
                normalized_query=after_slash or clean_q,
                slash_command="ticket",
            )

        if slash_cmd == "audit":
            # Distinguish read-only pending approval inspection vs initiating a new approval request
            has_submit_cue = (
                (amount is not None and amount > 0)
                or any(w in clean_lower for w in ("采购", "购买", "申请", "提交", "发起", "大额", "macbook", "服务器"))
            )
            is_read_only = (not after_slash) or (
                any(w in clean_lower for w in AUDIT_READ_ONLY_KEYWORDS) and not has_submit_cue
            )
            if is_read_only:
                return _build_route_result(
                    "chat",
                    metadata,
                    routing_method="slash_command",
                    confidence=1.0,
                    reason="slash_audit_status",
                    normalized_query=after_slash or "查看待审批单据状态",
                    slash_command="audit_status",
                )
            return _build_route_result(
                "approval",
                metadata,
                routing_method="slash_command",
                confidence=1.0,
                reason="slash_audit_submit",
                normalized_query=after_slash or clean_q,
                slash_command="audit_submit",
                parsed_amount=amount,
            )

    # Check @data_source directive from PromptBar metadata or inline @ tag
    resolved_source, query = _extract_data_source(raw_query, metadata)
    q_lower = query.lower()
    amount = parse_purchase_amount(query)

    if resolved_source == "db_mysql":
        comp_p, comp_s, comp_t = _detect_compound_intent(q_lower, query, amount)
        if comp_p and comp_s:
            return _build_route_result(
                comp_p,
                metadata,
                secondary_intent=comp_s,
                routing_method="data_source_directive",
                confidence=0.98,
                reason="data_source_mysql_compound",
                tool_hint=comp_t,
                normalized_query=query,
                data_source_resolved="db_mysql",
                parsed_amount=amount,
            )
        _, detected_hint, _ = _detect_tool_intent(q_lower, query)
        if not detected_hint:
            if any(w in q_lower for w in ("员工", "同事", "部门", "职级", "电话", "邮箱", "联系方式")):
                detected_hint = "query_employee"
            elif any(w in q_lower for w in ("工单", "故障", "报修")):
                detected_hint = "create_ticket"
            else:
                detected_hint = "query_inventory"
        return _build_route_result(
            "tool",
            metadata,
            routing_method="data_source_directive",
            confidence=0.98,
            reason="data_source_db_mysql",
            tool_hint=detected_hint,
            normalized_query=query,
            data_source_resolved="db_mysql",
            parsed_amount=amount,
        )

    if resolved_source == "erp_sap":
        if _is_policy_inquiry(q_lower) and not _has_explicit_action_submission(q_lower):
            return _build_route_result(
                "retrieve",
                metadata,
                routing_method="data_source_directive",
                confidence=0.95,
                reason="data_source_erp_policy_inquiry",
                normalized_query=query,
                data_source_resolved="erp_sap",
                parsed_amount=amount,
            )
        comp_p, comp_s, comp_t = _detect_compound_intent(q_lower, query, amount)
        if comp_p and comp_s:
            return _build_route_result(
                comp_p,
                metadata,
                secondary_intent=comp_s,
                routing_method="data_source_directive",
                confidence=0.98,
                reason="data_source_erp_compound",
                tool_hint=comp_t,
                normalized_query=query,
                data_source_resolved="erp_sap",
                parsed_amount=amount,
            )
        app_matched, _ = _detect_approval_intent(q_lower, query, amount)
        if app_matched:
            return _build_route_result(
                "approval",
                metadata,
                routing_method="data_source_directive",
                confidence=0.98,
                reason="data_source_erp_approval",
                normalized_query=query,
                data_source_resolved="erp_sap",
                parsed_amount=amount,
            )
        erp_tool_hint = (
            "create_purchase"
            if (_detect_purchase_without_amount(q_lower) or (any(w in q_lower for w in ("采购", "下单", "申购")) and amount is not None))
            else "query_inventory"
        )
        return _build_route_result(
            "tool",
            metadata,
            routing_method="data_source_directive",
            confidence=0.96,
            reason="data_source_erp_tool",
            tool_hint=erp_tool_hint,
            normalized_query=query,
            data_source_resolved="erp_sap",
            parsed_amount=amount,
        )

    if resolved_source == "kb_all":
        comp_p, comp_s, comp_t = _detect_compound_intent(q_lower, query, amount)
        return _build_route_result(
            "retrieve",
            metadata,
            secondary_intent=comp_s or "",
            routing_method="data_source_directive",
            confidence=0.98,
            reason="data_source_kb_all",
            tool_hint=comp_t,
            normalized_query=query,
            data_source_resolved="kb_all",
            parsed_amount=amount,
        )

    # ------------------------------------------------------------------
    # Tier 1A-bis: Active Multi-Turn Missing-Slot Clarification Continuation
    # ------------------------------------------------------------------
    clarification_ctx = detect_pending_clarification_context(messages, metadata, current_query=query)
    if clarification_ctx is not None:
        pending_tool = str(clarification_ctx["pending_tool"])
        prior_turns = list(clarification_ctx.get("prior_user_turns") or [])
        if pending_tool in ("create_purchase", "approval"):
            merged_amounts = merge_purchase_amounts_across_turns(prior_turns + [query])
            merged_total = merged_amounts.get("total_price")
            if isinstance(merged_total, (int, float)) and merged_total > APPROVAL_THRESHOLD_RMB:
                return _build_route_result(
                    "approval",
                    metadata,
                    routing_method="slot_clarification_resume",
                    confidence=0.97,
                    reason="slot_clarification_purchase_over_threshold",
                    normalized_query=query,
                    parsed_amount=float(merged_total),
                    preserve_pending_slots=True,
                )
            return _build_route_result(
                "tool",
                metadata,
                routing_method="slot_clarification_resume",
                confidence=0.97,
                reason="slot_clarification_purchase_continue",
                tool_hint="create_purchase",
                normalized_query=query,
                parsed_amount=float(merged_total) if isinstance(merged_total, (int, float)) else None,
                preserve_pending_slots=True,
            )
        return _build_route_result(
            "tool",
            metadata,
            routing_method="slot_clarification_resume",
            confidence=0.97,
            reason=f"slot_clarification_continue_{pending_tool}",
            tool_hint=pending_tool,
            normalized_query=query,
            parsed_amount=amount,
            preserve_pending_slots=True,
        )

    # ------------------------------------------------------------------
    # Tier 1B: Fast Deterministic Guardrails for Unambiguous Cases (0ms)
    # ------------------------------------------------------------------
    if _is_pure_chitchat(query):
        return _build_route_result(
            "chat",
            metadata,
            routing_method="deterministic_guard",
            confidence=0.99,
            reason="pure_chitchat_guard",
            normalized_query=query,
        )

    if _is_general_chat_utility(q_lower):
        return _build_route_result(
            "chat",
            metadata,
            routing_method="deterministic_guard",
            confidence=0.95,
            reason="general_chat_utility",
            normalized_query=query,
        )

    # Compound explicit two-step intent (e.g. "核对采购制度标准，并提交审批")
    comp_primary, comp_secondary, comp_tool = _detect_compound_intent(q_lower, query, amount)
    if comp_primary and comp_secondary:
        return _build_route_result(
            comp_primary,
            metadata,
            secondary_intent=comp_secondary,
            routing_method="deterministic_guard",
            confidence=0.95,
            reason=f"compound_{comp_primary}_{comp_secondary}",
            tool_hint=comp_tool,
            normalized_query=query,
            parsed_amount=amount,
        )

    # High-confidence explicit tool commands (e.g. "创建工单", "发邮件", "查询员工张伟")
    tool_matched, tool_hint, tool_high_conf = _detect_tool_intent(q_lower, query)
    if tool_matched and tool_high_conf:
        return _build_route_result(
            "tool",
            metadata,
            routing_method="deterministic_guard",
            confidence=0.96,
            reason=f"explicit_tool_{tool_hint or 'generic'}",
            tool_hint=tool_hint,
            normalized_query=query,
            parsed_amount=amount,
        )

    # High-confidence explicit high-value purchase approval (> 5,000 RMB or explicit approval trigger)
    approval_matched, approval_high_conf = _detect_approval_intent(q_lower, query, amount)
    if approval_matched and approval_high_conf:
        return _build_route_result(
            "approval",
            metadata,
            routing_method="deterministic_guard",
            confidence=0.96,
            reason="explicit_or_high_value_approval",
            normalized_query=query,
            parsed_amount=amount,
        )

    # Explicit purchase request without price/budget -> route to create_purchase for polite slot clarification
    if amount is None and _detect_purchase_without_amount(q_lower):
        return _build_route_result(
            "tool",
            metadata,
            routing_method="deterministic_guard",
            confidence=0.94,
            reason="explicit_purchase_without_amount",
            tool_hint="create_purchase",
            normalized_query=query,
        )

    # High-confidence unambiguous SOP / enterprise policy inquiry (no action submission cue)
    if _is_policy_inquiry(q_lower) and not _has_explicit_action_submission(q_lower):
        if any(kw in q_lower for kw in ENTERPRISE_KNOWLEDGE_KEYWORDS):
            return _build_route_result(
                "retrieve",
                metadata,
                routing_method="deterministic_guard",
                confidence=0.95,
                reason="explicit_policy_inquiry",
                normalized_query=query,
                parsed_amount=amount,
            )

    # ------------------------------------------------------------------
    # Tier 2: Lightweight Non-Thinking LLM Contextual Classifier (6 turns)
    # ------------------------------------------------------------------
    llm_decision = await _classify_with_llm(
        query=query,
        q_lower=q_lower,
        history=history,
        data_source=resolved_source,
    )
    if llm_decision is not None:
        return _build_route_result(
            llm_decision["intent"],
            metadata,
            secondary_intent=llm_decision["secondary_intent"],
            routing_method="llm_contextual",
            confidence=llm_decision["confidence"],
            reason=llm_decision["reason"],
            tool_hint=llm_decision["tool_hint"],
            normalized_query=query,
            parsed_amount=amount,
        )

    # ------------------------------------------------------------------
    # Tier 3: Enhanced Multi-Turn Deterministic Contextual Fallback
    # ------------------------------------------------------------------
    fb_intent, fb_secondary, fb_tool, fb_conf, fb_reason = _classify_deterministic_fallback(
        query=query,
        q_lower=q_lower,
        history=history,
        amount=amount,
    )
    return _build_route_result(
        fb_intent,
        metadata,
        secondary_intent=fb_secondary,
        routing_method="fallback_contextual_rules",
        confidence=fb_conf,
        reason=fb_reason,
        tool_hint=fb_tool,
        normalized_query=query,
        parsed_amount=amount,
    )
