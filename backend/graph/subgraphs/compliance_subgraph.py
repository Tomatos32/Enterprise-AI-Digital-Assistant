"""Compliance Domain Subgraph for Contract Auditing and Procurement Guardrails."""

from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage

from backend.graph.state import AgentState
from backend.tools.impl.purchase_tools import create_purchase


# 1. Compliance System Prompt
COMPLIANCE_SYSTEM_PROMPT = """你是一个专职于法务合规审查与采购风控防线的数字员工助手（Compliance Sub-Agent）。
你的职责范围严格限定在：
1. 商业采购合同法律风险条款扫描与违规排查 (review_contract_clause)
2. 采购申请风控合规校验与二级金额审批门禁管理 (create_purchase)
3. 外部合作供应商合规资质与黑白名单库核验 (check_compliance_whitelist)

安全防线红线：
- 严禁处理任何日常 HR 考勤查询或 IT 设备报修运维业务。
- 坚决执行采购超额防线：总价超过 5,000 元必须触发主管审批，超过 50,000 元必须触发合规总监审批。
- 严禁向存在严重失信或黑名单记录的供应商发起采购流转。
"""

# 2. Compliance Domain Specific Tools
MOCK_SUPPLIERS = {
    "Apple Official": {"is_whitelisted": True, "risk_level": "LOW", "category": "IT设备"},
    "Dell Enterprise": {"is_whitelisted": True, "risk_level": "LOW", "category": "IT设备"},
    "Herman Miller Official": {"is_whitelisted": True, "risk_level": "LOW", "category": "办公家具"},
    "Malicious Corp": {"is_whitelisted": False, "risk_level": "HIGH_BLACKLIST", "category": "违规皮包公司"},
}


def check_compliance_whitelist(supplier_name: str) -> Dict[str, Any]:
    """核验供应商是否在企业法务合规白名单内，排查高危失信供应商."""
    supplier = MOCK_SUPPLIERS.get(supplier_name)
    if not supplier:
        return {
            "status": "UNKNOWN",
            "supplier_name": supplier_name,
            "is_whitelisted": False,
            "risk_level": "MEDIUM_UNVERIFIED",
            "message": f"供应商 '{supplier_name}' 未在企业合格供应商库内，需补充法务准入尽调。",
        }

    if not supplier["is_whitelisted"]:
        return {
            "status": "BLOCKED",
            "supplier_name": supplier_name,
            "is_whitelisted": False,
            "risk_level": supplier["risk_level"],
            "message": f"【严重合规警报】供应商 '{supplier_name}' 位于法务失信惩戒黑名单中，禁止采购合作！",
        }

    return {
        "status": "VERIFIED",
        "supplier_name": supplier_name,
        "is_whitelisted": True,
        "risk_level": "LOW",
        "category": supplier["category"],
        "message": "供应商资质核查合格，准予合作。",
    }


def review_contract_clause(contract_title: str, contract_text: str) -> Dict[str, Any]:
    """智能扫描审查商业合同条款中的合规风险、保密协议、违约金上限与管辖法院."""
    risks = []

    if "违约金" in contract_text and ("50%" in contract_text or "100%" in contract_text):
        risks.append("违约金比例过高（超过法定标准），存在严重法务纠纷风险")
    if "不可抗力" not in contract_text:
        risks.append("未约定不可抗力免责条款，权利义务不对等")
    if "仲裁" not in contract_text and "法院" not in contract_text:
        risks.append("争议解决条款缺失管辖法院或仲裁机构明确约定")

    has_violation = len(risks) > 0
    return {
        "status": "COMPLETED",
        "contract_title": contract_title,
        "compliance_result": "HIGH_RISK" if has_violation else "PASSED",
        "risk_count": len(risks),
        "detected_risks": risks if risks else ["未检出明显重大违法违规条款"],
        "review_advice": "需法务律师介入修改风险条款" if has_violation else "条款合规，准予签署流转",
    }


# 3. Allowed Tools Whitelist
COMPLIANCE_ALLOWED_TOOLS = {
    "review_contract_clause": review_contract_clause,
    "create_purchase": create_purchase,
    "check_compliance_whitelist": check_compliance_whitelist,
}


def execute_compliance_tool(tool_name: str, **kwargs) -> Dict[str, Any]:
    """执行合规审查领域工具，若发生跨领域调用则抛出 PermissionError 实施物理拦截."""
    if tool_name not in COMPLIANCE_ALLOWED_TOOLS:
        raise PermissionError(
            f"Security Violation: Compliance Subgraph is prohibited from executing cross-domain tool '{tool_name}'. "
            f"Allowed tools: {list(COMPLIANCE_ALLOWED_TOOLS.keys())}"
        )
    tool_func = COMPLIANCE_ALLOWED_TOOLS[tool_name]
    return tool_func(**kwargs)


# 4. Compliance Subgraph Nodes
def compliance_reasoning_node(state: AgentState) -> Dict[str, Any]:
    """合规风控专职思考节点."""
    messages = list(state.get("messages", []))
    last_msg = messages[-1].content if messages else ""
    query = str(last_msg).lower()

    tool_call = None
    if "合同" in query or "条款" in query or "contract" in query:
        tool_call = {
            "tool": "review_contract_clause",
            "args": {
                "contract_title": "企业战略采购合作框架协议",
                "contract_text": "本协议双方合作，违约金设定为合同总额 100%，无争议管辖约定。",
            },
        }
    elif "供应商" in query or "黑名单" in query or "资质" in query or "supplier" in query:
        tool_call = {
            "tool": "check_compliance_whitelist",
            "args": {"supplier_name": "Apple Official"},
        }
    elif "采购" in query or "超额" in query or "purchase" in query:
        tool_call = {
            "tool": "create_purchase",
            "args": {
                "item_name": "MacBook Pro 16",
                "quantity": 5,
                "unit_price": 22999.0,
                "department": "IT运维部",
                "reason": "新入职架构师办公电脑采购",
            },
        }

    metadata = dict(state.get("metadata", {}))
    metadata["subgraph"] = "compliance"
    metadata["compliance_tool_call"] = tool_call
    return {"metadata": metadata}


def compliance_execution_node(state: AgentState) -> Dict[str, Any]:
    """合规工具调用与回复生成节点."""
    metadata = state.get("metadata", {})
    tool_call = metadata.get("compliance_tool_call")

    if tool_call:
        tool_name = tool_call["tool"]
        tool_args = tool_call.get("args", {})
        result = execute_compliance_tool(tool_name, **tool_args)
        response_text = f"【合规风控专职助手服务响应】已完成合规风控审查：{result}"
    else:
        response_text = (
            "【合规风控专职助手服务响应】您好，我是法务风控专职助手。我可以帮您扫描合同风险条款、校验供应商黑白名单或审核采购门禁。"
        )

    new_msg = AIMessage(content=response_text)
    return {"messages": [new_msg], "current_step": "compliance_completed"}


# 5. Build Compliance Subgraph
def build_compliance_subgraph():
    """构建并编译 Compliance 专职 Subgraph 状态机."""
    workflow = StateGraph(AgentState)
    workflow.add_node("compliance_reasoning", compliance_reasoning_node)
    workflow.add_node("compliance_execution", compliance_execution_node)

    workflow.set_entry_point("compliance_reasoning")
    workflow.add_edge("compliance_reasoning", "compliance_execution")
    workflow.add_edge("compliance_execution", END)

    return workflow.compile()


compliance_subgraph = build_compliance_subgraph()
