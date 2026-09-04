"""Unit Tests for Domain-Specific Subgraphs Decoupling and Security Tool Whitelist."""

import pytest
from langchain_core.messages import HumanMessage

from backend.graph.state import AgentState
from backend.graph.subgraphs import (
    hr_subgraph,
    finance_subgraph,
    it_subgraph,
    compliance_subgraph,
    HR_ALLOWED_TOOLS,
    FINANCE_ALLOWED_TOOLS,
    IT_ALLOWED_TOOLS,
    COMPLIANCE_ALLOWED_TOOLS,
    execute_hr_tool,
    execute_finance_tool,
    execute_it_tool,
    execute_compliance_tool,
    HR_SYSTEM_PROMPT,
    FINANCE_SYSTEM_PROMPT,
    IT_SYSTEM_PROMPT,
    COMPLIANCE_SYSTEM_PROMPT,
)


# ============================================================================
# 1. System Prompt & Tool Whitelist Definition Tests
# ============================================================================

def test_subgraphs_metadata_and_prompts():
    """验证各 Subgraph 拥有互相独立的专属 Prompt 与互斥的工具集."""
    assert "HR Sub-Agent" in HR_SYSTEM_PROMPT
    assert "Finance Sub-Agent" in FINANCE_SYSTEM_PROMPT
    assert "IT Sub-Agent" in IT_SYSTEM_PROMPT
    assert "Compliance Sub-Agent" in COMPLIANCE_SYSTEM_PROMPT

    # 验证工具集键名
    assert set(HR_ALLOWED_TOOLS.keys()) == {"query_employee", "query_attendance", "query_salary_slip"}
    assert set(FINANCE_ALLOWED_TOOLS.keys()) == {"verify_invoice", "check_budget", "submit_reimbursement"}
    assert set(IT_ALLOWED_TOOLS.keys()) == {"create_ticket", "query_inventory", "grant_system_permission"}
    assert set(COMPLIANCE_ALLOWED_TOOLS.keys()) == {"review_contract_clause", "create_purchase", "check_compliance_whitelist"}


# ============================================================================
# 2. Security Whitelist & Cross-Domain Permission Tests
# ============================================================================

def test_hr_tool_whitelist_and_cross_domain_protection():
    """验证 HR Subgraph 工具调用白名单与跨领域越权物理拦截."""
    # 正向工具调用
    res = execute_hr_tool("query_attendance", employee_id="EMP-1001", month="2026-08")
    assert res["status"] == "SUCCESS"
    assert res["attendance_rate"] == "100%"

    res_sal = execute_hr_tool("query_salary_slip", employee_id="EMP-1001", month="2026-08")
    assert res_sal["net_salary"] == 25600.0

    # 尝试跨领域调用财务/IT工具 -> 必须抛出 PermissionError
    with pytest.raises(PermissionError) as exc_info:
        execute_hr_tool("verify_invoice", invoice_code="123", invoice_number="456", amount=100)
    assert "Security Violation: HR Subgraph is prohibited" in str(exc_info.value)

    with pytest.raises(PermissionError) as exc_info:
        execute_hr_tool("create_ticket", title="IT Help", description="Repair")
    assert "Security Violation: HR Subgraph is prohibited" in str(exc_info.value)


def test_finance_tool_whitelist_and_cross_domain_protection():
    """验证 Finance Subgraph 工具调用白名单与预算超限熔断、跨领域拦截."""
    # 发票查验
    inv = execute_finance_tool("verify_invoice", invoice_code="01100", invoice_number="9988", amount=500.0)
    assert inv["status"] == "VALID"
    assert inv["verified"] is True

    # 预算正常报销
    reimb_ok = execute_finance_tool(
        "submit_reimbursement", applicant_id="EMP-1001", department="研发部", amount=1000.0
    )
    assert reimb_ok["status"] == "APPROVED"

    # 预算超限熔断
    reimb_fail = execute_finance_tool(
        "submit_reimbursement", applicant_id="EMP-1001", department="研发部", amount=9999999.0
    )
    assert reimb_fail["status"] == "REJECTED"
    assert "已被财务风控自动熔断拦截" in reimb_fail["message"]

    # 跨领域越权拦截
    with pytest.raises(PermissionError) as exc_info:
        execute_finance_tool("query_salary_slip", employee_id="EMP-1001")
    assert "Security Violation: Finance Subgraph is prohibited" in str(exc_info.value)


def test_it_tool_whitelist_and_cross_domain_protection():
    """验证 IT Subgraph 工具调用白名单与跨领域越权拦截."""
    # 正常权限申请
    perm = execute_it_tool(
        "grant_system_permission", applicant_id="EMP-1001", system_name="VPN", permission_level="read"
    )
    assert perm["status"] == "SUBMITTED"

    # 跨领域越权拦截
    with pytest.raises(PermissionError) as exc_info:
        execute_it_tool("submit_reimbursement", applicant_id="EMP-1001", department="IT", amount=100)
    assert "Security Violation: IT Subgraph is prohibited" in str(exc_info.value)


def test_compliance_tool_whitelist_and_cross_domain_protection():
    """验证 Compliance Subgraph 合同审查、黑名单拦截与跨领域拦截."""
    # 合同高风险审查
    risky_contract = execute_compliance_tool(
        "review_contract_clause",
        contract_title="合作协议",
        contract_text="违约金设定为合同总额 100%，无争议管辖约定",
    )
    assert risky_contract["compliance_result"] == "HIGH_RISK"
    assert risky_contract["risk_count"] >= 2

    # 供应商白名单核验
    white = execute_compliance_tool("check_compliance_whitelist", supplier_name="Apple Official")
    assert white["status"] == "VERIFIED"
    assert white["is_whitelisted"] is True

    # 供应商黑名单拦截
    black = execute_compliance_tool("check_compliance_whitelist", supplier_name="Malicious Corp")
    assert black["status"] == "BLOCKED"
    assert "位于法务失信惩戒黑名单中" in black["message"]

    # 跨领域越权拦截
    with pytest.raises(PermissionError) as exc_info:
        execute_compliance_tool("query_attendance", employee_id="EMP-1001")
    assert "Security Violation: Compliance Subgraph is prohibited" in str(exc_info.value)


# ============================================================================
# 3. Subgraph End-to-End Workflow Execution Tests
# ============================================================================

def test_hr_subgraph_execution_flow():
    """验证 HR Subgraph 状态机端到端执行（查询工资/考勤）."""
    state: AgentState = {
        "messages": [HumanMessage(content="我想查询一下我上个月的工资薪酬明细")],
        "user_id": "EMP-1001",
        "session_id": "session-hr-01",
    }
    result = hr_subgraph.invoke(state)
    assert "messages" in result
    last_msg = result["messages"][-1].content
    assert "【HR专职助手服务响应】" in last_msg
    assert "net_salary" in last_msg
    assert result.get("current_step") == "hr_completed"


def test_finance_subgraph_execution_flow():
    """验证 Finance Subgraph 状态机端到端执行（查询部门预算）."""
    state: AgentState = {
        "messages": [HumanMessage(content="请帮我核对一下今年研发部的预算额度是多少")],
        "user_id": "EMP-1001",
        "session_id": "session-fin-01",
    }
    result = finance_subgraph.invoke(state)
    assert "messages" in result
    last_msg = result["messages"][-1].content
    assert "【财务专职助手服务响应】" in last_msg
    assert "available_budget" in last_msg
    assert result.get("current_step") == "finance_completed"


def test_it_subgraph_execution_flow():
    """验证 IT Subgraph 状态机端到端执行（申报办公网络故障报修）."""
    state: AgentState = {
        "messages": [HumanMessage(content="我的工位网络断了，需要紧急报修工单")],
        "user_id": "EMP-1001",
        "session_id": "session-it-01",
    }
    result = it_subgraph.invoke(state)
    assert "messages" in result
    last_msg = result["messages"][-1].content
    assert "【IT专职运维助手服务响应】" in last_msg
    assert result.get("current_step") == "it_completed"


def test_compliance_subgraph_execution_flow():
    """验证 Compliance Subgraph 状态机端到端执行（合同条款合规扫描）."""
    state: AgentState = {
        "messages": [HumanMessage(content="请审核这份商业采购合同条款是否存在合规法律风险")],
        "user_id": "EMP-1001",
        "session_id": "session-comp-01",
    }
    result = compliance_subgraph.invoke(state)
    assert "messages" in result
    last_msg = result["messages"][-1].content
    assert "【合规风控专职助手服务响应】" in last_msg
    assert result.get("current_step") == "compliance_completed"
