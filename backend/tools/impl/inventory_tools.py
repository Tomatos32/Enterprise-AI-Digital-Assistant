"""Equipment Inventory Query Tool Implementation."""

from typing import Optional, Dict, Any
from backend.tools.registry import register_tool

# Realistic mock corporate hardware asset inventory
MOCK_INVENTORY = [
    {
        "item_id": "DEV-001",
        "item_name": "MacBook Pro 16",
        "spec": "M3 Max / 36G / 1TB",
        "unit_price": 22999,
        "stock": 12,
        "department": "IT运维部",
        "status": "In Stock"
    },
    {
        "item_id": "DEV-002",
        "item_name": "Dell UltraSharp 显示器",
        "spec": "27英寸 4K U2723QE",
        "unit_price": 3499,
        "stock": 28,
        "department": "行政后勤部",
        "status": "In Stock"
    },
    {
        "item_id": "DEV-003",
        "item_name": "Herman Miller 办公椅",
        "spec": "Aeron 人体工学椅",
        "unit_price": 9800,
        "stock": 8,
        "department": "行政后勤部",
        "status": "In Stock"
    },
    {
        "item_id": "DEV-004",
        "item_name": "ThinkPad X1 Carbon",
        "spec": "i7-1370P / 32G / 1TB",
        "unit_price": 14999,
        "stock": 15,
        "department": "IT运维部",
        "status": "In Stock"
    },
    {
        "item_id": "DEV-005",
        "item_name": "Logitech MX Master 3S",
        "spec": "无线蓝牙鼠标 8000DPI",
        "unit_price": 699,
        "stock": 45,
        "department": "行政后勤部",
        "status": "In Stock"
    },
    {
        "item_id": "DEV-006",
        "item_name": "Mac Studio",
        "spec": "M2 Ultra / 64G / 2TB",
        "unit_price": 31999,
        "stock": 5,
        "department": "设计部",
        "status": "In Stock"
    },
    {
        "item_id": "DEV-007",
        "item_name": "Dell PowerEdge R760 服务器",
        "spec": "2x Xeon 6430 / 256G",
        "unit_price": 85000,
        "stock": 3,
        "department": "IT运维部",
        "status": "Running"
    }
]


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
    """Queries equipment inventory stock and specifications."""
    matched = []
    query = item_name.lower()
    for item in MOCK_INVENTORY:
        if query in item["item_name"].lower() or query in item["spec"].lower():
            if category and category.lower() not in item["department"].lower():
                continue
            matched.append(item)

    if matched:
        return {
            "status": "SUCCESS",
            "count": len(matched),
            "data": matched
        }
    return {
        "status": "NOT_FOUND",
        "count": 0,
        "message": f"未找到匹配 '{item_name}' 的设备库存"
    }
