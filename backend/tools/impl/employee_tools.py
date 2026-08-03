"""Employee Query Tool Implementation."""

from typing import Optional, Dict, Any
from backend.tools.registry import register_tool

# Realistic mock corporate employee directory
MOCK_EMPLOYEES = [
    {
        "employee_id": "EMP-1001",
        "name": "张伟",
        "department": "IT运维部",
        "title": "资深运维工程师",
        "rank": "P6",
        "email": "zhangwei@company.com",
        "status": "Active",
        "join_date": "2022-03-15"
    },
    {
        "employee_id": "EMP-1002",
        "name": "李娜",
        "department": "研发部",
        "title": "资深后端架构师",
        "rank": "P7",
        "email": "lina@company.com",
        "status": "Active",
        "join_date": "2021-06-10"
    },
    {
        "employee_id": "EMP-1003",
        "name": "王强",
        "department": "行政后勤部",
        "title": "行政经理",
        "rank": "M2",
        "email": "wangqiang@company.com",
        "status": "Active",
        "join_date": "2020-11-01"
    },
    {
        "employee_id": "EMP-1004",
        "name": "陈明",
        "department": "财务部",
        "title": "财务总监",
        "rank": "M3",
        "email": "chenming@company.com",
        "status": "Active",
        "join_date": "2019-04-20"
    },
    {
        "employee_id": "EMP-1005",
        "name": "赵敏",
        "department": "HR部",
        "title": "人力资源总监",
        "rank": "M3",
        "email": "zhaomin@company.com",
        "status": "Active",
        "join_date": "2018-08-12"
    }
]


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
    """Queries corporate employee records by name and department."""
    matched = []
    for emp in MOCK_EMPLOYEES:
        if name in emp["name"]:
            if department and department not in emp["department"]:
                continue
            matched.append(emp)

    if matched:
        return {
            "status": "SUCCESS",
            "count": len(matched),
            "data": matched
        }
    return {
        "status": "NOT_FOUND",
        "count": 0,
        "message": f"未找到姓名包含 '{name}' 的员工信息"
    }
