"""Purchase Request Tool Implementation."""

import random
from datetime import datetime
from typing import Dict, Any
from backend.tools.registry import register_tool


@register_tool(
    name="create_purchase",
    description="提交企业采购申请单，计算总金额并自动匹配 Human-in-the-loop 金额审批门禁",
    parameters={
        "type": "object",
        "properties": {
            "item_name": {"type": "string", "description": "采购物品/服务名称 (例如: MacBook Pro, 显示器)"},
            "quantity": {"type": "integer", "description": "采购数量 (必须大于 0)"},
            "unit_price": {"type": "number", "description": "预估单价 (单位: 元 RMB)"},
            "department": {"type": "string", "description": "申请部门 (例如: IT运维部, 研发部)"},
            "reason": {"type": "string", "description": "采购申请事由说明"}
        },
        "required": ["item_name", "quantity", "unit_price", "department"]
    }
)
def create_purchase(
    item_name: str,
    quantity: int,
    unit_price: float,
    department: str,
    reason: str = "办公设备采购"
) -> Dict[str, Any]:
    """Creates a procurement purchase order and checks approval threshold rules."""
    if quantity <= 0:
        return {"status": "ERROR", "message": "采购数量必须大于 0"}
    if unit_price <= 0:
        return {"status": "ERROR", "message": "预估单价必须大于 0"}

    total_price = round(quantity * unit_price, 2)
    po_num = random.randint(1000, 9999)
    today_str = datetime.now().strftime("%Y%m%d")
    purchase_id = f"PO-{today_str}-{po_num}"

    # Determine approval threshold node according to DOC-PROC-2026-002 SOP
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

    return {
        "status": "SUCCESS",
        "purchase_id": purchase_id,
        "item_name": item_name,
        "quantity": quantity,
        "unit_price": unit_price,
        "total_price": total_price,
        "department": department,
        "reason": reason,
        "approval_status": approval_status,
        "approval_node": approval_node,
        "action_note": action_note,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
