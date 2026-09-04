"""IT Domain Subgraph for Device Incidents, Permissions, and Service Tickets."""

from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage

from backend.graph.state import AgentState
from backend.tools.impl.ticket_tools import create_ticket
from backend.tools.impl.inventory_tools import query_inventory


# 1. IT System Prompt
IT_SYSTEM_PROMPT = """你是一个专职于企业 IT 运维与技术支持的数字员工助手（IT Sub-Agent）。
你的职责范围严格限定在：
1. IT 运维与服务工单报修创建 (create_ticket)
2. 办公 IT 设备规格与库存查询 (query_inventory)
3. 员工内网系统、VPN 与代码权限开通申请 (grant_system_permission)

安全防线红线：
- 严禁处理任何非 IT 领域的业务（如财务报销审批、人事考勤修改、采购合同审查等）。
- 对 P0/P1 等重大事故必须自动注入快速响应 SLA 承诺。
- 严禁执行未在 IT 授权白名单内的外部工具调用。
"""

# 2. IT Domain Specific Tools
def grant_system_permission(
    applicant_id: str,
    system_name: str,
    permission_level: str = "read",
    reason: str = "工作需要",
) -> Dict[str, Any]:
    """提交企业内部系统访问权限申请（如 VPN、GitLab、云控制台）."""
    valid_levels = {"read", "write", "admin"}
    lvl = permission_level.lower()
    if lvl not in valid_levels:
        lvl = "read"

    return {
        "status": "SUBMITTED",
        "permission_request_id": f"PERM-2026-{applicant_id[-4:]}",
        "applicant_id": applicant_id,
        "system_name": system_name,
        "permission_level": lvl,
        "reason": reason,
        "sla": "1 个工作日内完成审批与策略下发",
    }


# 3. Allowed Tools Whitelist
IT_ALLOWED_TOOLS = {
    "create_ticket": create_ticket,
    "query_inventory": query_inventory,
    "grant_system_permission": grant_system_permission,
}


def execute_it_tool(tool_name: str, **kwargs) -> Dict[str, Any]:
    """执行 IT 运维领域工具，若发生跨领域调用则抛出 PermissionError 实施物理拦截."""
    if tool_name not in IT_ALLOWED_TOOLS:
        raise PermissionError(
            f"Security Violation: IT Subgraph is prohibited from executing cross-domain tool '{tool_name}'. "
            f"Allowed tools: {list(IT_ALLOWED_TOOLS.keys())}"
        )
    tool_func = IT_ALLOWED_TOOLS[tool_name]
    return tool_func(**kwargs)


# 4. IT Subgraph Nodes
def it_reasoning_node(state: AgentState) -> Dict[str, Any]:
    """IT 运维专职思考节点."""
    messages = list(state.get("messages", []))
    last_msg = messages[-1].content if messages else ""
    query = str(last_msg).lower()

    tool_call = None
    if "报修" in query or "故障" in query or "工单" in query or "ticket" in query:
        tool_call = {
            "tool": "create_ticket",
            "args": {
                "title": "办公网络连接异常故障报修",
                "description": "工位网线接口无法获取 IP 地址",
                "priority": "P2",
                "department": "IT",
            },
        }
    elif "库存" in query or "电脑" in query or "设备" in query or "inventory" in query:
        tool_call = {
            "tool": "query_inventory",
            "args": {"item_name": "MacBook Pro 16"},
        }
    elif "权限" in query or "vpn" in query or "permission" in query or "gitlab" in query:
        tool_call = {
            "tool": "grant_system_permission",
            "args": {
                "applicant_id": state.get("user_id", "EMP-1001"),
                "system_name": "生产环境只读运维控制台",
                "permission_level": "read",
            },
        }

    metadata = dict(state.get("metadata", {}))
    metadata["subgraph"] = "it"
    metadata["it_tool_call"] = tool_call
    return {"metadata": metadata}


def it_execution_node(state: AgentState) -> Dict[str, Any]:
    """IT 工具调用与回复生成节点."""
    metadata = state.get("metadata", {})
    tool_call = metadata.get("it_tool_call")

    if tool_call:
        tool_name = tool_call["tool"]
        tool_args = tool_call.get("args", {})
        result = execute_it_tool(tool_name, **tool_args)
        response_text = f"【IT专职运维助手服务响应】已处理您的技术服务请求：{result}"
    else:
        response_text = (
            "【IT专职运维助手服务响应】您好，我是 IT 服务中心专职助手。我可以帮您提报故障工单、查询设备库存或申请系统访问权限。"
        )

    new_msg = AIMessage(content=response_text)
    return {"messages": [new_msg], "current_step": "it_completed"}


# 5. Build IT Subgraph
def build_it_subgraph():
    """构建并编译 IT 专职 Subgraph 状态机."""
    workflow = StateGraph(AgentState)
    workflow.add_node("it_reasoning", it_reasoning_node)
    workflow.add_node("it_execution", it_execution_node)

    workflow.set_entry_point("it_reasoning")
    workflow.add_edge("it_reasoning", "it_execution")
    workflow.add_edge("it_execution", END)

    return workflow.compile()


it_subgraph = build_it_subgraph()
