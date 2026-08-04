"""Intent Router Node Implementation for LangGraph State Machine."""

from backend.graph.state import AgentState


async def router_node(state: AgentState) -> dict:
    """
    Intent Router Node that analyzes user queries and determines routing target.
    Routes execution to 'retrieve', 'tool', 'approval', or 'chat' branch.
    """
    # 1. Check if intent is explicitly set in state or metadata (Override)
    if state.get("intent"):
        return {
            "intent": state["intent"],
            "current_step": "routed"
        }

    metadata = state.get("metadata", {})
    if "override_intent" in metadata:
        return {
            "intent": metadata["override_intent"],
            "current_step": "routed"
        }

    # 2. Extract last message and check for tool_calls attribute on AIMessage
    messages = state.get("messages", [])
    if messages:
        last_msg = messages[-1]
        tool_calls = getattr(last_msg, "tool_calls", None)
        if tool_calls:
            return {
                "intent": "tool",
                "current_step": "routed"
            }
        query = str(getattr(last_msg, "content", "")).lower()
    else:
        query = ""

    # 3. Intent Classification Rules
    retrieve_keywords = [
        "sop", "图文版", "规定", "文档", "政策", "手册", "规章",
        "报销", "sla", "考勤", "年假", "检索", "查询", "标准", "差旅", "福利", "流程"
    ]
    approval_keywords = ["发起审批", "人机协同", "大额采购", "批准", "会签", "需主管审批"]
    tool_keywords = [
        "创建工单", "发邮件", "创建采购单", "调用工具", "提交申请",
        "ticket", "email", "purchase", "create_ticket", "send_email",
        "申请设备", "报修"
    ]

    intent = "chat"
    if any(kw in query for kw in retrieve_keywords) and not any(action in query for action in ["提交", "发起", "申请采购", "执行"]):
        intent = "retrieve"
    elif any(kw in query for kw in approval_keywords):
        intent = "approval"
    elif any(kw in query for kw in tool_keywords):
        if "采购" in query and ("6000" in query or "10000" in query or "大额" in query or "审批" in query):
            intent = "approval"
        else:
            intent = "tool"
    elif any(kw in query for kw in retrieve_keywords):
        intent = "retrieve"

    return {
        "intent": intent,
        "current_step": "routed"
    }
