"""Human-in-the-Loop Approval Node with LangGraph Interrupt & Resume Controls."""

import random
from datetime import datetime
from typing import Dict, Any
from langgraph.types import interrupt
from langchain_core.messages import AIMessage
from backend.graph.state import AgentState
import backend.db.session as db_session
from backend.models.approval import Approval
from backend.tools.impl import create_purchase


async def approval_node(state: AgentState) -> Dict[str, Any]:
    """
    Human-in-the-loop Approval Node.
    Triggers LangGraph interrupt() when purchase amount > 5,000 RMB,
    pausing state machine execution until主管 approval API resume action.
    """
    metadata = state.get("metadata", {}).copy()
    purchase_args = metadata.get("purchase_args", {})

    # Extract purchase parameters
    item_name = purchase_args.get("item_name", "办公设备")
    quantity = int(purchase_args.get("quantity", 1))
    unit_price = float(purchase_args.get("unit_price", 6000.0))
    department = purchase_args.get("department", "IT运维部")
    reason = purchase_args.get("reason", "硬件升级需求")
    total_price = round(quantity * unit_price, 2)

    # Thread ID for checkpoint matching
    thread_id = metadata.get("thread_id", "thread_default")

    # Threshold Check: If total_price > 5,000 RMB -> Human-in-the-loop Approval required
    if total_price > 5000:
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
                created_at=datetime.utcnow()
            )
            db.add(app_obj)
            db.commit()

        # 2. Trigger LangGraph Interrupt (State Machine Paused here until resumed via Command)
        resume_data = interrupt({
            "approval_id": approval_id,
            "thread_id": thread_id,
            "item_name": item_name,
            "total_price": total_price,
            "department": department,
            "reason": reason,
            "status": "PENDING",
            "message": f"采购单总额 ￥{total_price:,.2f} 超过 5,000 元阈值，已触发人机协同中断，等待主管审批。"
        })

        # 3. Execution Resumed via Command(resume=...)
        action = "approve"
        if isinstance(resume_data, dict):
            action = resume_data.get("action", "approve")
        elif isinstance(resume_data, str):
            action = resume_data.lower()

        if action == "approve":
            res = create_purchase(item_name=item_name, quantity=quantity, unit_price=unit_price, department=department, reason=reason)
            res["approval_status"] = "APPROVED_BY_SUPERVISOR"
            ai_text = f"[人机协同审批结果] 主管已批准该采购单 ({approval_id})！最终采购单号: {res.get('purchase_id')}，金额: ￥{total_price:,.2f}。"
        else:
            ai_text = f"[人机协同审批结果] 主管已拒绝该采购单 ({approval_id})。理由: 部门预估超支，暂不予批准。"
            res = {"status": "REJECTED", "approval_id": approval_id, "total_price": total_price}
    else:
        # <= 5000 RMB -> Auto Approved
        res = create_purchase(item_name=item_name, quantity=quantity, unit_price=unit_price, department=department, reason=reason)
        ai_text = f"[系统自动审批] 采购金额 ￥{total_price:,.2f} <= 5,000 元，系统已自动完成审核与 ERP 下发。"

    metadata["approval_result"] = res
    metadata["approval_executed"] = True

    return {
        "messages": [AIMessage(content=ai_text)],
        "metadata": metadata,
        "current_step": "approval_completed"
    }
