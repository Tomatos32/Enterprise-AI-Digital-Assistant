"""Intent Router Node Implementation for LangGraph State Machine.

Employs a RAG-First enterprise policy routing engine with high-precision chat/greeting
guards, approval gates, and external tool execution dispatching.
"""

import re
from typing import Dict, Any
from backend.graph.state import AgentState


# Pure conversational greetings and small talk guards
GREETING_WORDS = {
    "你好", "您好", "hi", "hello", "hey", "早上好", "中午好", "下午好", "晚上好",
    "在吗", "在不在", "哈喽", "嗨", "您好啊", "你好呀", "早安", "晚安",
    "很高兴见到你", "认识你很高兴", "初次见面", "幸会", "辛苦了", "请多关照",
}

ACK_WORDS = {
    "谢谢", "感谢", "多谢", "好的", "收到", "明白", "行", "可以的",
    "ok", "okay", "thanks", "thank you", "再见", "拜拜", "bye",
}

IDENTITY_WORDS = {
    "你是谁", "介绍一下你自己", "你能做什么", "帮助", "help",
    "功能介绍", "你的名字", "你会做什么",
}


def _is_pure_chitchat(query: str) -> bool:
    """Detects whether user query is purely a conversational greeting or formality."""
    cleaned = re.sub(r"[^\w一-鿿]", "", query.lower()).strip()
    if not cleaned:
        return True
    if cleaned in GREETING_WORDS or cleaned in ACK_WORDS or cleaned in IDENTITY_WORDS:
        return True
    # Strip greetings from start (e.g. "你好你是谁" -> "你是谁")
    remainder = cleaned
    for g in sorted(GREETING_WORDS, key=len, reverse=True):
        if remainder.startswith(g):
            remainder = remainder[len(g):].strip()
    if not remainder or remainder in GREETING_WORDS or remainder in ACK_WORDS or remainder in IDENTITY_WORDS:
        return True
    # Also check if it's an identity/help question without enterprise business entities
    if any(id_word in cleaned for id_word in ["你是谁", "介绍一下自己", "自我介绍", "你能做什么", "你的名字", "功能介绍"]):
        if not any(domain_w in cleaned for domain_w in ["制度", "规章", "报销", "借用", "出差", "采购", "工单", "配置", "标准"]):
            return True
    return False


async def router_node(state: AgentState) -> Dict[str, Any]:
    """Intent Router Node that analyzes user queries and determines routing target.

    Routes execution to 'retrieve' (RAG), 'tool', 'approval', or 'chat' branch.
    """
    # 1. Explicit Intent Overrides from State or Metadata
    if state.get("intent"):
        return {
            "intent": state["intent"],
            "current_step": "routed",
        }

    metadata = state.get("metadata", {}) or {}
    if "override_intent" in metadata:
        return {
            "intent": metadata["override_intent"],
            "current_step": "routed",
        }

    # If user explicitly bound or tagged a data source (@知识源), prioritize RAG retrieval
    if metadata.get("data_source") or metadata.get("attached_source"):
        return {
            "intent": "retrieve",
            "current_step": "routed",
        }

    # 2. Extract last message and check for tool_calls attribute on AIMessage
    messages = state.get("messages", [])
    if messages:
        last_msg = messages[-1]
        tool_calls = getattr(last_msg, "tool_calls", None)
        if tool_calls:
            return {
                "intent": "tool",
                "current_step": "routed",
            }
        query = str(getattr(last_msg, "content", "")).strip()
    else:
        query = ""

    if not query:
        return {
            "intent": "chat",
            "current_step": "routed",
        }

    q_lower = query.lower()

    # 3. Pure Chat & Social Formality Guard (Executed first for greetings like "你好", "hi", "你是谁")
    if _is_pure_chitchat(query):
        return {"intent": "chat", "current_step": "routed"}

    # 4. Action Tool Intent Gate (Explicit external operational execution commands)
    # Checks for ticket, email, employee query, inventory query
    is_employee_query = ("员工" in q_lower or "employee" in q_lower) and any(
        act in q_lower for act in ["查", "信息", "岗位", "联系方式", "是谁", "电话", "邮箱", "职级"]
    )
    is_inventory_query = ("库存" in q_lower or "inventory" in q_lower) and any(
        act in q_lower for act in ["查", "余量", "备件", "数量"]
    )
    is_ticket_op = any(kw in q_lower for kw in ["创建工单", "新建工单", "提工单", "报修", "create_ticket"])
    is_email_op = any(kw in q_lower for kw in ["发邮件", "发送邮件", "send_email"])
    is_tool_call_keyword = any(kw in q_lower for kw in ["调用工具", "执行工具", "execute_tool"])

    if is_employee_query or is_inventory_query or is_ticket_op or is_email_op or is_tool_call_keyword:
        return {"intent": "tool", "current_step": "routed"}

    # 5. Approval Intent Gate (High-Value / Human-in-the-Loop workflows)
    # Notice: If query is asking about SOP/policy rules (e.g. "查询采购与审批SOP门禁"), it belongs to retrieve!
    is_asking_sop = any(w in q_lower for w in ["sop", "图文版", "规章", "规定", "文档", "政策", "手册", "细则", "指南", "查询", "检索"])
    approval_keywords = [
        "发起审批", "人机协同", "大额采购", "会签", "需主管审批",
        "提交审批", "申请大额", "审批单", "提交大额采购",
    ]
    if any(kw in q_lower for kw in approval_keywords):
        return {"intent": "approval", "current_step": "routed"}

    # Purchase with large amount and requesting action (not just querying policy)
    if not is_asking_sop and ("采购" in q_lower or "购买" in q_lower) and any(
        amt in q_lower for amt in ["6000", "10000", "22999", "大额", "超额"]
    ):
        return {"intent": "approval", "current_step": "routed"}

    # 6. RAG-First Enterprise Policy & Knowledge Intent
    # Informational domain keywords spanning IT, HR, Finance, Procurement, Security, CS
    enterprise_knowledge_keywords = [
        # SOP & Guidelines
        "sop", "图文版", "规定", "文档", "政策", "手册", "规章", "指南", "制度", "流程",
        "标准", "规范", "细则", "条款", "合规",
        # IT & Workstation & Asset SLA (03_IT)
        "备用机", "借用", "借机", "归还", "外借", "电脑", "笔记本", "macbook", "thinkpad",
        "显示器", "外设", "资产", "设备", "折旧", "换新", "硬件", "配置", "vpn", "ztna",
        "密码", "mfa", "权限", "开源协议", "密钥", "服务器", "集群", "故障", "sla",
        "p0", "p1", "p2", "p3", "p4", "响应时间", "解决时间",
        # Procurement & Purchasing (02_PROCUREMENT)
        "采购", "供应商", "询价", "招标", "验收", "领用", "固定资产", "审批",
        # HR, Attendance & Welfare (01_HR)
        "人事", "考勤", "打卡", "请假", "年假", "事假", "病假", "产假", "育儿假",
        "迟到", "早退", "旷工", "加班", "社保", "公积金", "薪酬", "工资", "调薪",
        "绩效", "年终奖", "离职", "交接", "试用期", "转正", "福利", "招聘", "录用", "入职",
        # Finance & Travel (04_FINANCE)
        "财务", "报销", "出差", "差旅", "住宿", "机票", "高铁", "交通补贴", "餐补",
        "借款", "发票", "预算", "额度", "单价", "超额",
        # Security & Compliance (05_SECURITY)
        "安全", "保密", "泄密", "数据安全", "知识产权", "禁令", "脱敏", "审计", "密级",
        # CS (06_CS)
        "售后", "投诉", "退换货", "回访",
        # Question / Inquiry Terms
        "多久", "几天", "多长", "多少", "期限", "要求", "条件", "怎么", "如何",
        "能否", "是否可以", "可否", "有何规定", "能不能", "可以吗", "怎么申请", "怎么办理",
        "检索", "查询",
    ]

    if any(kw in q_lower for kw in enterprise_knowledge_keywords):
        return {"intent": "retrieve", "current_step": "routed"}

    # Default strategy for Enterprise Assistant: informational queries default to RAG retrieval
    if len(query) >= 4:
        return {"intent": "retrieve", "current_step": "routed"}

    return {
        "intent": "chat",
        "current_step": "routed",
    }

