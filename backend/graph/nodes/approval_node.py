"""Human-in-the-Loop Approval Node with Semantic Slot Validation & Interrupt Controls."""

import random
from datetime import datetime
from typing import Any, Dict

from langchain_core.messages import AIMessage
from langgraph.types import interrupt

import backend.db.session as db_session
from backend.graph.state import AgentState
from backend.models.approval import Approval
from backend.tools.impl import create_purchase
from backend.tools.slot_extractor import (
    APPROVAL_THRESHOLD_RMB,
    extract_slots_for_tool,
)


async def approval_node(state: AgentState) -> Dict[str, Any]:
    """
    Human-in-the-loop Approval Node.
    Validates real purchase slots via explicit metadata['purchase_args'] or semantic
    slot extraction (Strategy 5.2 Option A: never fabricates catalog prices or defaults).
      - Missing item_name or positive price -> zero DB writes, zero interrupt(), polite clarification.
      - total_price > 5,000 RMB -> persists PENDING Approval & pauses via LangGraph interrupt().
      - total_price <= 5,000 RMB -> auto-approves & executes create_purchase directly.
    """
    messages = list(state.get("messages", []))
    last_msg = messages[-1] if messages else None
    raw_query = str(getattr(last_msg, "content", "")) if last_msg else ""

    metadata = dict(state.get("metadata") or {})
    query = str(metadata.get("normalized_query") or raw_query).strip() or raw_query
    metadata.pop("escalate_to_approval", None)

    extraction = await extract_slots_for_tool(
        tool_name="approval",
        query=query,
        messages=messages,
        metadata=metadata,
    )
    metadata["slot_extraction_method"] = extraction.extraction_method
    metadata["slot_merged_from_history"] = extraction.merged_from_history

    # Missing required purchase slots -> zero DB writes, zero interrupt()
    if not extraction.is_complete:
        metadata["approval_executed"] = False
        metadata["slot_clarification_needed"] = True
        metadata["slot_clarification_question"] = extraction.clarification_question
        metadata["missing_slots"] = list(extraction.missing_slots)
        metadata["pending_slot_tool"] = "approval"
        metadata["pending_slots"] = dict(extraction.slots)
        return {
            "metadata": metadata,
            "current_step": "slot_clarification_needed",
        }

    # Clear pending clarification flags once complete
    metadata.pop("slot_clarification_needed", None)
    metadata.pop("slot_clarification_question", None)
    metadata.pop("missing_slots", None)
    metadata.pop("pending_slot_tool", None)
    metadata.pop("pending_slots", None)

    item_name = str(extraction.slots["item_name"])
    quantity = int(extraction.slots.get("quantity", 1))
    unit_price = round(float(extraction.slots["unit_price"]), 2)
    department = str(extraction.slots.get("department") or metadata.get("department") or "未指定部门")
    reason = str(extraction.slots.get("reason") or "办公设备采购")
    applicant = str(metadata.get("display_name") or state.get("user_id") or "当前申请人")
    total_price = round(quantity * unit_price, 2)

    thread_id = str(metadata.get("thread_id") or "thread_default")

    # Threshold Check: If total_price > 5,000 RMB -> Human-in-the-loop Approval required
    if total_price > APPROVAL_THRESHOLD_RMB:
        today_str = datetime.now().strftime("%Y%m%d")
        app_num = random.randint(1000, 9999)
        approval_id = f"APP-{today_str}-{app_num}"

        # 1. Create Pending Approval Record in Database
        with db_session.SessionLocal() as db:
            app_obj = Approval(
                approval_id=approval_id,
                thread_id=thread_id,
                item_name=item_name,
                quantity=quantity,
                unit_price=unit_price,
                total_price=total_price,
                department=department,
                reason=reason,
                status="PENDING",
                created_at=datetime.utcnow(),
            )
            db.add(app_obj)
            db.commit()

        # 2. Trigger LangGraph Interrupt with full authentic payload
        resume_data = interrupt(
            {
                "approval_id": approval_id,
                "thread_id": thread_id,
                "item_name": item_name,
                "quantity": quantity,
                "unit_price": unit_price,
                "total_price": total_price,
                "department": department,
                "applicant": applicant,
                "reason": reason,
                "status": "PENDING",
                "message": f"采购单总额 ￥{total_price:,.2f} 超过 5,000 元阈值，已触发人机协同中断，等待主管审批。",
            }
        )

        # 3. Execution Resumed via Command(resume=...)
        action = "approve"
        if isinstance(resume_data, dict):
            action = str(resume_data.get("action", "approve")).lower()
        elif isinstance(resume_data, str):
            action = resume_data.lower()

        if action == "approve":
            res = create_purchase(
                item_name=item_name,
                quantity=quantity,
                unit_price=unit_price,
                department=department,
                reason=reason,
            )
            res["approval_status"] = "APPROVED_BY_SUPERVISOR"
            ai_text = (
                f"[人机协同审批结果] 主管已批准该采购单 ({approval_id})，"
                f"采购物品：{item_name} × {quantity}，单价 ￥{unit_price:,.2f}，"
                f"最终采购单号：{res.get('purchase_id')}，总额：￥{total_price:,.2f}。"
            )
        else:
            ai_text = (
                f"[人机协同审批结果] 主管已驳回该采购单 ({approval_id})，"
                f"采购物品：{item_name} × {quantity}（总额 ￥{total_price:,.2f}）。"
            )
            res = {"status": "REJECTED", "approval_id": approval_id, "total_price": total_price}
    else:
        # <= 5000 RMB -> Auto Approved (zero interrupt)
        res = create_purchase(
            item_name=item_name,
            quantity=quantity,
            unit_price=unit_price,
            department=department,
            reason=reason,
        )
        ai_text = (
            f"[系统自动审批] 采购物品 {item_name} × {quantity}（单价 ￥{unit_price:,.2f}），"
            f"总金额 ￥{total_price:,.2f} 未超过 5,000 元阈值，系统已自动审核并下发 ERP（单号：{res.get('purchase_id')}）。"
        )

    metadata["approval_result"] = res
    metadata["approval_executed"] = True
    metadata["extracted_purchase_args"] = {
        "item_name": item_name,
        "quantity": quantity,
        "unit_price": unit_price,
        "total_price": total_price,
        "department": department,
        "applicant": applicant,
        "reason": reason,
    }

    return {
        "messages": [AIMessage(content=ai_text)],
        "metadata": metadata,
        "current_step": "approval_completed",
    }
