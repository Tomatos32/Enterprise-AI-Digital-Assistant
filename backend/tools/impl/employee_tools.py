"""Employee Query Tool Implementation with Unified Adapter Delegation."""

from typing import Optional, Dict, Any
from backend.tools.registry import register_tool
from backend.adapters.factory import get_hr_adapter


@register_tool(
    name="query_employee",
    description="查询企业员工基本信息、所属部门、职级及联系方式",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "员工姓名 (例如: 张伟, 李娜)"},
            "department": {"type": "string", "description": "可选部门过滤 (例如: IT运维部, 研发部)"}
        },
        "required": ["name"]
    }
)
def query_employee(name: str, department: Optional[str] = None) -> Dict[str, Any]:
    """Queries employee records via Unified HR Adapter with seamless Mock/Prod switching."""
    adapter = get_hr_adapter()
    return adapter.get_employee(id_or_name=name, department=department)
