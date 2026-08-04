"""Approval Management & Human-in-the-Loop Control REST API Router."""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from langgraph.types import Command
from backend.db.session import get_db
from backend.models.approval import Approval
from backend.graph.workflow import graph

router = APIRouter()


class ApprovalActionRequest(BaseModel):
    approval_id: str = Field(..., description="审批单唯一编号 (如 APP-20260804-1001)")
    action: str = Field(..., description="决策操作: approve 或 reject")
    comment: Optional[str] = Field("主管审核意见", description="可选审批批注说明")


@router.post("/action")
async def process_approval_action(
    req: ApprovalActionRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Approval Action API: Processes supervisor decision (approve/reject),
    updates Approval DB record, and calls graph.ainvoke(Command(resume=...)) to resume LangGraph.
    """
    act = req.action.lower()
    if act not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="action 参数必须为 'approve' 或 'reject'")

    app_obj = db.query(Approval).filter(Approval.approval_id == req.approval_id).first()
    if not app_obj:
        raise HTTPException(status_code=404, detail=f"未找到编号为 '{req.approval_id}' 的审批记录")

    if app_obj.status != "PENDING":
        return {
            "status": "ALREADY_PROCESSED",
            "approval_id": app_obj.approval_id,
            "current_status": app_obj.status,
            "message": f"该审批单已处于 '{app_obj.status}' 状态，无需重复处理"
        }

    # 1. Update DB Record
    app_obj.status = "APPROVED" if act == "approve" else "REJECTED"
    db.commit()
    db.refresh(app_obj)

    # 2. Resume LangGraph Execution via Command(resume=...)
    config = {"configurable": {"thread_id": app_obj.thread_id}}
    graph_res = None
    try:
        graph_res = await graph.ainvoke(Command(resume={"action": act}), config=config)
    except Exception as e:
        graph_res = {"error": str(e)}

    return {
        "status": "SUCCESS",
        "approval_id": app_obj.approval_id,
        "thread_id": app_obj.thread_id,
        "action": act,
        "db_status": app_obj.status,
        "graph_output": str(graph_res.get("messages", [])[-1].content) if graph_res and "messages" in graph_res else "Resumed"
    }


@router.get("/pending")
def list_pending_approvals(
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Lists all pending human-in-the-loop approvals."""
    pending_items = db.query(Approval).filter(Approval.status == "PENDING").all()
    data = [
        {
            "approval_id": a.approval_id,
            "thread_id": a.thread_id,
            "item_name": a.item_name,
            "quantity": a.quantity,
            "unit_price": a.unit_price,
            "total_price": a.total_price,
            "department": a.department,
            "reason": a.reason,
            "status": a.status,
            "created_at": a.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }
        for a in pending_items
    ]
    return {
        "status": "SUCCESS",
        "count": len(data),
        "data": data
    }
