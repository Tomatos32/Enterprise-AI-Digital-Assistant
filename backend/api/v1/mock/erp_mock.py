"""ERP Enterprise System Mock REST API Router."""

import random
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from backend.db.session import get_db
from backend.models.inventory import Inventory
from backend.models.purchase import Purchase
from backend.db.seed import seed_initial_data

router = APIRouter()


class PurchaseCreateRequest(BaseModel):
    item_name: str = Field(..., description="采购物品名称")
    quantity: int = Field(..., gt=0, description="采购数量")
    unit_price: float = Field(..., gt=0, description="预估单价")
    department: str = Field(..., description="申请部门")
    reason: Optional[str] = Field("办公采购", description="事由说明")


@router.get("/inventory")
def get_inventory(
    item_name: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Mock ERP API: Query equipment inventory from database.
    """
    seed_initial_data(db)

    query = db.query(Inventory)
    if item_name:
        query = query.filter(Inventory.item_name.like(f"%{item_name}%"))
    if category:
        query = query.filter(Inventory.department.like(f"%{category}%"))

    items = query.all()
    if not items:
        return {
            "status": "NOT_FOUND",
            "count": 0,
            "message": "未找到匹配的设备库存"
        }

    data = [
        {
            "item_id": i.item_id,
            "item_name": i.item_name,
            "spec": i.spec,
            "unit_price": i.unit_price,
            "stock": i.stock,
            "department": i.department,
            "status": i.status
        }
        for i in items
    ]

    return {
        "status": "SUCCESS",
        "count": len(data),
        "data": data
    }


@router.post("/purchases")
def create_purchase_order(
    req: PurchaseCreateRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Mock ERP API: Submit a purchase order and store into Purchase table with approval threshold rules.
    """
    total_price = round(req.quantity * req.unit_price, 2)
    po_num = random.randint(1000, 9999)
    today_str = datetime.now().strftime("%Y%m%d")
    purchase_id = f"PO-{today_str}-{po_num}"

    # Threshold rules according to DOC-PROC-2026-002 SOP
    if total_price <= 5000:
        approval_status = "AUTO_APPROVED"
        approval_node = "系统自动通过"
        action_note = "Agent 直接调用 create_purchase() 提交 ERP"
    elif 5000 < total_price <= 50000:
        approval_status = "PENDING_SUPERVISOR_APPROVAL"
        approval_node = "部门主管审批"
        action_note = "Agent 触发 Interrupt 状态等待主管确认 (Human-in-the-loop)"
    elif 50000 < total_price <= 200000:
        approval_status = "PENDING_EXECUTIVE_APPROVAL"
        approval_node = "主管 + 财务总监 + 采购总监联签"
        action_note = "触发多重会签流程，校验部门季度预算"
    else:
        approval_status = "PENDING_BOARD_APPROVAL"
        approval_node = "主管 + 财务总监 + 法务 VP + CEO + 董事会决议"
        action_note = "强制启动招投标 (RFP)，评审委员会审查"

    po_obj = Purchase(
        purchase_id=purchase_id,
        item_name=req.item_name,
        quantity=req.quantity,
        unit_price=req.unit_price,
        total_price=total_price,
        department=req.department,
        reason=req.reason,
        approval_status=approval_status,
        approval_node=approval_node,
        action_note=action_note,
        created_at=datetime.utcnow()
    )
    db.add(po_obj)
    db.commit()
    db.refresh(po_obj)

    return {
        "status": "SUCCESS",
        "purchase_id": po_obj.purchase_id,
        "item_name": po_obj.item_name,
        "quantity": po_obj.quantity,
        "unit_price": po_obj.unit_price,
        "total_price": po_obj.total_price,
        "department": po_obj.department,
        "reason": po_obj.reason,
        "approval_status": po_obj.approval_status,
        "approval_node": po_obj.approval_node,
        "action_note": po_obj.action_note,
        "created_at": po_obj.created_at.strftime("%Y-%m-%d %H:%M:%S")
    }
