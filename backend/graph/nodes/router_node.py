"""Intent Router Node Implementation for LangGraph State Machine."""

from backend.graph.state import AgentState


async def router_node(state: AgentState) -> dict:
    """
    Intent Router Node that analyzes user queries and determines routing target.
    Routes execution to 'retrieve', 'tool', or 'chat' branch.
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

    # 2. Extract last user query message
    messages = state.get("messages", [])
    query = ""
    if messages:
        last_msg = messages[-1]
        query = str(getattr(last_msg, "content", "")).lower()

    # 3. Intent Classification Rules
    retrieve_keywords = [
        "采购", "报销", "sop", "规章", "制度", "sla", "考勤",
        "年假", "规定", "检索", "查询", "标准", "差旅", "福利",
        "政策", "流程", "发票", "IT", "病假", "退款"
    ]
    tool_keywords = [
        "创建工单", "发邮件", "创建采购单", "调用工具", "提交申请",
        "ticket", "email", "purchase", "create_ticket", "send_email"
    ]

    intent = "chat"
    if any(kw in query for kw in tool_keywords):
        intent = "tool"
    elif any(kw in query for kw in retrieve_keywords):
        intent = "retrieve"

    return {
        "intent": intent,
        "current_step": "routed"
    }
