"""Service Ticket Creation Tool Implementation with Unified Adapter Delegation."""

from typing import Dict, Any
from backend.tools.registry import register_tool
from backend.adapters.factory import get_oa_adapter


@register_tool(
    name="create_ticket",
    description="提交 IT 运维或 HR 服务工单，并返回工单编号及 SLA 服务响应承诺",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "工单简短标题 (例如: 核心网络瘫痪, 软件密码重置)"},
            "description": {"type": "string", "description": "工单详细故障或需求描述"},
            "priority": {"type": "string", "description": "故障等级 (P0 灾难, P1 紧急, P2 重要, P3 一般, P4 咨询), 默认为 P3"},
            "department": {"type": "string", "description": "受理部门 (IT 或 HR), 默认为 IT"}
        },
        "required": ["title", "description"]
    }
)
def create_ticket(
    title: str,
    description: str,
    priority: str = "P3",
    department: str = "IT"
) -> Dict[str, Any]:
    """Creates a new service ticket via Unified OA Adapter."""
    adapter = get_oa_adapter()
    return adapter.create_ticket(
        title=title,
        description=description,
        priority=priority,
        department=department
    )
