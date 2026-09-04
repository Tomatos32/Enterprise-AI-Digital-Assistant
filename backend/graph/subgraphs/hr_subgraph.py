"""HR Domain Subgraph for Employee Info, Attendance, and Salary Management."""

from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage

from backend.graph.state import AgentState
from backend.tools.impl.employee_tools import query_employee


# 1. HR System Prompt
HR_SYSTEM_PROMPT = """你是一个专职于人力资源（HR）领域的数字员工助手（HR Sub-Agent）。
你的职责范围严格限定在：
1. 员工基础档案与职级信息查询 (query_employee)
2. 员工考勤记录与打卡统计查询 (query_attendance)
3. 员工薪资明细与个税扣缴核对 (query_salary_slip)

安全防线红线：
- 严禁处理任何非 HR 领域的请求（如财务发票报销、IT系统权限开通、采购审批等）。
- 若检测到跨领域问题或未授权工具调用请求，必须坚决拒绝并提示用户流转至对应专职部门。
"""

# 2. HR Domain Specific Tools
def query_attendance(employee_id: str, month: str = "2026-08") -> Dict[str, Any]:
    """查询指定员工的月度出勤、缺卡、迟到与请假天数."""
    return {
        "status": "SUCCESS",
        "employee_id": employee_id,
        "month": month,
        "work_days": 22,
        "actual_attended_days": 22,
        "late_count": 0,
        "leave_days": 0.0,
        "attendance_rate": "100%",
    }


def query_salary_slip(employee_id: str, month: str = "2026-08") -> Dict[str, Any]:
    """查询指定员工月度薪酬工资条明细（包含基本工资、绩效与扣除项）."""
    return {
        "status": "SUCCESS",
        "employee_id": employee_id,
        "month": month,
        "base_salary": 25000.0,
        "performance_bonus": 5000.0,
        "social_security_deduction": 2600.0,
        "individual_income_tax": 1800.0,
        "net_salary": 25600.0,
        "currency": "CNY",
    }


# 3. Allowed Tools Whitelist
HR_ALLOWED_TOOLS = {
    "query_employee": query_employee,
    "query_attendance": query_attendance,
    "query_salary_slip": query_salary_slip,
}


def execute_hr_tool(tool_name: str, **kwargs) -> Dict[str, Any]:
    """执行 HR 领域工具，若发生跨领域调用则抛出 PermissionError 实施物理拦截."""
    if tool_name not in HR_ALLOWED_TOOLS:
        raise PermissionError(
            f"Security Violation: HR Subgraph is prohibited from executing cross-domain tool '{tool_name}'. "
            f"Allowed tools: {list(HR_ALLOWED_TOOLS.keys())}"
        )
    tool_func = HR_ALLOWED_TOOLS[tool_name]
    return tool_func(**kwargs)


# 4. HR Subgraph Nodes
def hr_reasoning_node(state: AgentState) -> Dict[str, Any]:
    """HR 专职思考节点."""
    messages = list(state.get("messages", []))
    last_msg = messages[-1].content if messages else ""
    query = str(last_msg).lower()

    # 意图识别与工具决策
    tool_call = None
    if "工资" in query or "薪酬" in query or "salary" in query:
        tool_call = {"tool": "query_salary_slip", "args": {"employee_id": state.get("user_id", "EMP-1001")}}
    elif "考勤" in query or "打卡" in query or "attendance" in query:
        tool_call = {"tool": "query_attendance", "args": {"employee_id": state.get("user_id", "EMP-1001")}}
    elif "员工" in query or "同事" in query or "employee" in query:
        tool_call = {"tool": "query_employee", "args": {"keyword": "张伟"}}

    metadata = dict(state.get("metadata", {}))
    metadata["subgraph"] = "hr"
    metadata["hr_tool_call"] = tool_call
    return {"metadata": metadata}


def hr_execution_node(state: AgentState) -> Dict[str, Any]:
    """HR 工具调用与回复生成节点."""
    metadata = state.get("metadata", {})
    tool_call = metadata.get("hr_tool_call")

    if tool_call:
        tool_name = tool_call["tool"]
        tool_args = tool_call.get("args", {})
        result = execute_hr_tool(tool_name, **tool_args)
        response_text = f"【HR专职助手服务响应】已为您查询人事数据：{result}"
    else:
        response_text = (
            "【HR专职助手服务响应】您好，我是人事行政专职助手。我可以帮您查询员工档案、出勤记录或薪资条。"
        )

    new_msg = AIMessage(content=response_text)
    return {"messages": [new_msg], "current_step": "hr_completed"}


# 5. Build HR Subgraph
def build_hr_subgraph():
    """构建并编译 HR 专职 Subgraph 状态机."""
    workflow = StateGraph(AgentState)
    workflow.add_node("hr_reasoning", hr_reasoning_node)
    workflow.add_node("hr_execution", hr_execution_node)

    workflow.set_entry_point("hr_reasoning")
    workflow.add_edge("hr_reasoning", "hr_execution")
    workflow.add_edge("hr_execution", END)

    return workflow.compile()


hr_subgraph = build_hr_subgraph()
