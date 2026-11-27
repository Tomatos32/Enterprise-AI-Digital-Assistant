"""Tool Execution Node Implementation with Hybrid Semantic Slot Extraction."""

import json
import logging
from typing import Any, Dict, List

from langchain_core.messages import ToolMessage

from backend.graph.state import AgentState
from backend.tools import registry
from backend.tools.slot_extractor import (
    APPROVAL_THRESHOLD_RMB,
    extract_slots_for_tool,
)

logger = logging.getLogger(__name__)


def _resolve_target_tool(query: str, tool_hint: str) -> str:
    """Resolves canonical target tool name from router tool_hint or lexical fallback."""
    if tool_hint in (
        "create_ticket",
        "create_purchase",
        "send_email",
        "query_employee",
        "query_inventory",
        "search_knowledge_base",
    ):
        return tool_hint

    q_lower = query.lower()
    if any(k in q_lower for k in ("工单", "ticket", "报修")):
        return "create_ticket"
    if any(k in q_lower for k in ("采购", "purchase", "申购", "下单")):
        return "create_purchase"
    if any(k in q_lower for k in ("邮件", "email", "mail")):
        return "send_email"
    if any(k in q_lower for k in ("员工", "employee", "同事", "工号")):
        return "query_employee"
    if any(k in q_lower for k in ("检索", "制度", "规章", "搜索知识", "查文档", "search_knowledge")):
        return "search_knowledge_base"
    return "query_inventory"


async def tool_node(state: AgentState) -> Dict[str, Any]:
    """
    Tool Node that intercepts structured tool_calls on AIMessage or extracts real semantic
    slots for routed tool intents without hardcoded fake defaults.

    Behaviors:
      - Structured AIMessage.tool_calls -> executes directly (100% backward compatible).
      - Missing required slots -> zero DB/tool side-effects, sets slot_clarification_needed.
      - Completed create_purchase with total_price > 5,000 RMB -> escalates acyclically
        to approval_node so supervisor approval gate is never bypassed.
    """
    messages = list(state.get("messages", []))
    last_msg = messages[-1] if messages else None

    new_messages: List[ToolMessage] = []
    metadata = dict(state.get("metadata") or {})
    context_docs: List[Dict[str, Any]] = []

    # 1. Explicit OpenAI/LangGraph tool_calls path (100% preserved)
    tool_calls = getattr(last_msg, "tool_calls", None) if last_msg else None

    if tool_calls:
        metadata["tool_executed"] = True
        for call in tool_calls:
            tool_name = call.get("name", "")
            tool_args = call.get("args", {})
            call_id = call.get("id", f"call_{tool_name}")

            try:
                res = await registry.execute_tool(tool_name, tool_args)
                content_str = json.dumps(res, ensure_ascii=False) if isinstance(res, (dict, list)) else str(res)
                if tool_name == "search_knowledge_base" and isinstance(res, dict) and "documents" in res:
                    context_docs.extend(res["documents"])
            except Exception as exc:
                content_str = json.dumps({"status": "ERROR", "message": str(exc)}, ensure_ascii=False)

            new_messages.append(
                ToolMessage(content=content_str, tool_call_id=call_id, name=tool_name)
            )
            metadata["tool_output"] = content_str

        result_state: Dict[str, Any] = {
            "messages": new_messages,
            "metadata": metadata,
            "current_step": "tool_executed",
        }
        if context_docs:
            result_state["context"] = context_docs
        return result_state

    # 2. Semantic Slot Extraction Path (zero fake defaults)
    raw_query = str(getattr(last_msg, "content", "")) if last_msg else ""
    query = str(metadata.get("normalized_query") or raw_query).strip() or raw_query
    tool_hint = str(metadata.get("tool_hint") or "").strip()
    tool_name = _resolve_target_tool(query, tool_hint)

    extraction = await extract_slots_for_tool(
        tool_name=tool_name,
        query=query,
        messages=messages,
        metadata=metadata,
    )
    metadata["slot_extraction_method"] = extraction.extraction_method
    metadata["slot_merged_from_history"] = extraction.merged_from_history
    if extraction.resolved_from_hr:
        metadata["slot_resolved_from_hr"] = True

    # 2A. Missing required slots -> zero tool execution, zero DB writes, polite clarification
    if not extraction.is_complete:
        metadata["tool_executed"] = False
        metadata["slot_clarification_needed"] = True
        metadata["slot_clarification_question"] = extraction.clarification_question
        metadata["missing_slots"] = list(extraction.missing_slots)
        metadata["pending_slot_tool"] = tool_name
        metadata["pending_slots"] = dict(extraction.slots)
        metadata.pop("escalate_to_approval", None)
        return {
            "metadata": metadata,
            "current_step": "slot_clarification_needed",
        }

    # Clear pending clarification state once all required slots are complete
    metadata.pop("slot_clarification_needed", None)
    metadata.pop("slot_clarification_question", None)
    metadata.pop("missing_slots", None)
    metadata.pop("pending_slot_tool", None)
    metadata.pop("pending_slots", None)

    # 2B. Dynamic 5,000 RMB approval escalation guard for create_purchase
    if tool_name == "create_purchase":
        qty = int(extraction.slots.get("quantity", 1))
        unit_price = float(extraction.slots.get("unit_price", 0.0))
        total_price = round(qty * unit_price, 2)
        if total_price > APPROVAL_THRESHOLD_RMB:
            metadata["tool_executed"] = False
            metadata["escalate_to_approval"] = True
            metadata["purchase_args"] = {
                "item_name": extraction.slots["item_name"],
                "quantity": qty,
                "unit_price": unit_price,
                "department": extraction.slots.get("department") or metadata.get("department") or "未指定部门",
                "reason": extraction.slots.get("reason") or "办公设备采购",
            }
            logger.info(
                "[ToolNode] Escalating purchase '%s' (total ￥%.2f > ￥%.0f) to approval_node.",
                extraction.slots["item_name"],
                total_price,
                APPROVAL_THRESHOLD_RMB,
            )
            return {
                "metadata": metadata,
                "current_step": "escalated_to_approval",
            }

    # 2C. Execute tool with verified semantic slots only
    exec_args = {
        k: v
        for k, v in extraction.slots.items()
        if not k.startswith("_") and k != "total_price" and v is not None
    }
    metadata["tool_executed"] = True
    metadata["extracted_tool_args"] = exec_args
    metadata.pop("escalate_to_approval", None)

    try:
        res = await registry.execute_tool(tool_name, exec_args)
        content_str = json.dumps(res, ensure_ascii=False) if isinstance(res, (dict, list)) else str(res)
        if tool_name == "search_knowledge_base" and isinstance(res, dict) and "documents" in res:
            context_docs.extend(res["documents"])
    except Exception as exc:
        content_str = json.dumps({"status": "ERROR", "message": str(exc)}, ensure_ascii=False)

    new_messages.append(
        ToolMessage(content=content_str, tool_call_id=f"call_{tool_name}_auto", name=tool_name)
    )
    metadata["tool_output"] = content_str

    result_state = {
        "messages": new_messages,
        "metadata": metadata,
        "current_step": "tool_executed",
    }
    if context_docs:
        result_state["context"] = context_docs
    return result_state
