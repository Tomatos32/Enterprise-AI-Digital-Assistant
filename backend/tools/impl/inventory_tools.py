"""Equipment Inventory Query Tool Implementation with Unified Adapter Delegation."""

from typing import Optional, Dict, Any
from backend.tools.registry import register_tool
from backend.adapters.factory import get_erp_adapter


@register_tool(
    name="query_inventory",
    description="查询办公设备及 IT 资产的规格、单价、库存数量及保管部门",
    parameters={
        "type": "object",
        "properties": {
            "item_name": {"type": "string", "description": "设备名称 (例如: MacBook, 显示器, 办公椅)"},
            "category": {"type": "string", "description": "可选类别或保管部门"}
        },
        "required": ["item_name"]
    }
)
def query_inventory(item_name: str, category: Optional[str] = None) -> Dict[str, Any]:
    """Queries equipment inventory stock via Unified ERP Adapter."""
    adapter = get_erp_adapter()
    return adapter.get_inventory(item_name=item_name, category=category)
