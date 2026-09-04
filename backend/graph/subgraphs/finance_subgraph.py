"""Finance Domain Subgraph for Invoices, Reimbursements, and Budget Auditing."""

from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage

from backend.graph.state import AgentState


# 1. Finance System Prompt
FINANCE_SYSTEM_PROMPT = """你是一个专职于财务结算与资金风控的数字员工助手（Finance Sub-Agent）。
你的职责范围严格限定在：
1. 增值税发票真伪查验与验真核销 (verify_invoice)
2. 部门财年预算额度与剩余可用资金查询 (check_budget)
3. 员工费用报销单据提交与合规预审 (submit_reimbursement)

安全防线红线：
- 严禁处理任何非财务领域的请求（如员工考勤打卡、IT设备维修申报、软件开发等）。
- 严密监控预算防线，单笔报销超额或预算不足时必须熔断并提示转人工特批。
- 若检测到跨领域工具调用，必须实施安全拦截。
"""

# 2. Finance Domain Specific Tools
def verify_invoice(invoice_code: str, invoice_number: str, amount: float) -> Dict[str, Any]:
    """校验增值税发票真伪、开票状态与金额一致性."""
    return {
        "status": "VALID",
        "invoice_code": invoice_code,
        "invoice_number": invoice_number,
        "amount": round(amount, 2),
        "seller": "企业级技术服务提供商",
        "tax_rate": "6%",
        "verified": True,
        "verification_time": "2026-09-04 10:00:00",
    }


def check_budget(department: str, fiscal_year: int = 2026) -> Dict[str, Any]:
    """查询指定部门全财年总预算、已消耗额度与可用余额."""
    return {
        "status": "SUCCESS",
        "department": department,
        "fiscal_year": fiscal_year,
        "total_budget": 500000.0,
        "consumed_budget": 185000.0,
        "available_budget": 315000.0,
        "utilization_rate": "37.0%",
    }


def submit_reimbursement(
    applicant_id: str,
    department: str,
    amount: float,
    category: str = "差旅交通费",
) -> Dict[str, Any]:
    """提交费用报销申请，自动校验部门剩余可用预算."""
    budget = check_budget(department)
    if amount > budget["available_budget"]:
        return {
            "status": "REJECTED",
            "message": f"报销金额 ¥{amount} 超出部门当前可用预算余额 ¥{budget['available_budget']}，已被财务风控自动熔断拦截！",
            "applicant_id": applicant_id,
        }

    return {
        "status": "APPROVED",
        "claim_id": f"EXP-202609-{applicant_id[-4:]}",
        "applicant_id": applicant_id,
        "department": department,
        "amount": round(amount, 2),
        "category": category,
        "message": "报销申请预审通过，已进入财务打款结算队列。",
    }


# 3. Allowed Tools Whitelist
FINANCE_ALLOWED_TOOLS = {
    "verify_invoice": verify_invoice,
    "check_budget": check_budget,
    "submit_reimbursement": submit_reimbursement,
}


def execute_finance_tool(tool_name: str, **kwargs) -> Dict[str, Any]:
    """执行财务领域工具，若发生跨领域调用则抛出 PermissionError 实施物理拦截."""
    if tool_name not in FINANCE_ALLOWED_TOOLS:
        raise PermissionError(
            f"Security Violation: Finance Subgraph is prohibited from executing cross-domain tool '{tool_name}'. "
            f"Allowed tools: {list(FINANCE_ALLOWED_TOOLS.keys())}"
        )
    tool_func = FINANCE_ALLOWED_TOOLS[tool_name]
    return tool_func(**kwargs)


# 4. Finance Subgraph Nodes
def finance_reasoning_node(state: AgentState) -> Dict[str, Any]:
    """财务专职思考节点."""
    messages = list(state.get("messages", []))
    last_msg = messages[-1].content if messages else ""
    query = str(last_msg).lower()

    tool_call = None
    if "发票" in query or "验真" in query or "invoice" in query:
        tool_call = {
            "tool": "verify_invoice",
            "args": {"invoice_code": "011002200111", "invoice_number": "88239102", "amount": 1280.0},
        }
    elif "预算" in query or "额度" in query or "budget" in query:
        tool_call = {
            "tool": "check_budget",
            "args": {"department": "研发部", "fiscal_year": 2026},
        }
    elif "报销" in query or "差旅" in query or "reimbursement" in query:
        tool_call = {
            "tool": "submit_reimbursement",
            "args": {
                "applicant_id": state.get("user_id", "EMP-1001"),
                "department": "研发部",
                "amount": 450.0,
                "category": "市内交通与差旅补贴",
            },
        }

    metadata = dict(state.get("metadata", {}))
    metadata["subgraph"] = "finance"
    metadata["finance_tool_call"] = tool_call
    return {"metadata": metadata}


def finance_execution_node(state: AgentState) -> Dict[str, Any]:
    """财务工具调用与回复生成节点."""
    metadata = state.get("metadata", {})
    tool_call = metadata.get("finance_tool_call")

    if tool_call:
        tool_name = tool_call["tool"]
        tool_args = tool_call.get("args", {})
        result = execute_finance_tool(tool_name, **tool_args)
        response_text = f"【财务专职助手服务响应】已完成财务核算处理：{result}"
    else:
        response_text = (
            "【财务专职助手服务响应】您好，我是财务共享专职助手。我可以帮您查验发票真伪、核对部门预算或提交报销单。"
        )

    new_msg = AIMessage(content=response_text)
    return {"messages": [new_msg], "current_step": "finance_completed"}


# 5. Build Finance Subgraph
def build_finance_subgraph():
    """构建并编译 Finance 专职 Subgraph 状态机."""
    workflow = StateGraph(AgentState)
    workflow.add_node("finance_reasoning", finance_reasoning_node)
    workflow.add_node("finance_execution", finance_execution_node)

    workflow.set_entry_point("finance_reasoning")
    workflow.add_edge("finance_reasoning", "finance_execution")
    workflow.add_edge("finance_execution", END)

    return workflow.compile()


finance_subgraph = build_finance_subgraph()
