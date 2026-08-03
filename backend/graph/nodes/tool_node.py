"""Tool Execution Node Implementation for LangGraph State Machine."""

import json
from typing import Dict, Any, List
from langchain_core.messages import ToolMessage
from backend.graph.state import AgentState
from backend.tools import registry


async def tool_node(state: AgentState) -> Dict[str, Any]:
    """
    Tool Node that intercepts tool_calls on AIMessage or processes tool intents,
    executes registered tools via ToolRegistry, and appends ToolMessage objects to state.
    """
    messages = state.get("messages", [])
    last_msg = messages[-1] if messages else None

    new_messages: List[ToolMessage] = []
    metadata = state.get("metadata", {}).copy()
    metadata["tool_executed"] = True

    # 1. Check if last message contains OpenAI/LangGraph tool_calls attribute
    tool_calls = getattr(last_msg, "tool_calls", None) if last_msg else None

    if tool_calls:
        for call in tool_calls:
            tool_name = call.get("name", "")
            tool_args = call.get("args", {})
            call_id = call.get("id", f"call_{tool_name}")

            try:
                res = await registry.execute_tool(tool_name, tool_args)
                content_str = json.dumps(res, ensure_ascii=False) if isinstance(res, (dict, list)) else str(res)
            except Exception as e:
                content_str = json.dumps({"status": "ERROR", "message": str(e)}, ensure_ascii=False)

            new_messages.append(
                ToolMessage(content=content_str, tool_call_id=call_id, name=tool_name)
            )
            metadata["tool_output"] = content_str
    else:
        # 2. Fallback keyword-based execution for state intent == "tool"
        query = str(getattr(last_msg, "content", "")) if last_msg else ""
        q_lower = query.lower()

        if "工单" in q_lower or "ticket" in q_lower:
            res = await registry.execute_tool("create_ticket", {"title": "客服支持工单", "description": query, "priority": "P2"})
            tool_name = "create_ticket"
        elif "采购" in q_lower or "purchase" in q_lower:
            res = await registry.execute_tool("create_purchase", {"item_name": "办公硬件设备", "quantity": 1, "unit_price": 6000.0, "department": "IT运维部", "reason": query})
            tool_name = "create_purchase"
        elif "邮件" in q_lower or "email" in q_lower:
            res = await registry.execute_tool("send_email", {"to_email": "admin@company.com", "subject": "系统自动化通知", "body": query})
            tool_name = "send_email"
        elif "员工" in q_lower or "employee" in q_lower:
            res = await registry.execute_tool("query_employee", {"name": "张伟"})
            tool_name = "query_employee"
        else:
            res = await registry.execute_tool("query_inventory", {"item_name": "MacBook"})
            tool_name = "query_inventory"

        content_str = json.dumps(res, ensure_ascii=False) if isinstance(res, (dict, list)) else str(res)
        new_messages.append(
            ToolMessage(content=content_str, tool_call_id=f"call_{tool_name}_auto", name=tool_name)
        )
        metadata["tool_output"] = content_str

    return {
        "messages": new_messages,
        "metadata": metadata,
        "current_step": "tool_executed"
    }
