"""Purchase Request Tool Implementation with Unified Adapter Delegation."""

from typing import Dict, Any
from backend.tools.registry import register_tool
from backend.adapters.factory import get_erp_adapter


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
    """Creates a procurement purchase order via Unified ERP Adapter."""
    adapter = get_erp_adapter()
    return adapter.create_purchase(
        item_name=item_name,
        quantity=quantity,
        unit_price=unit_price,
        department=department,
        reason=reason
    )
