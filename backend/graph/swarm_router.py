"""LangGraph Swarm Collaboration Protocol and Cross-Department Handoff Message Bus."""

from typing import Dict, Any, List, Optional, Annotated, Sequence, TypedDict
import operator
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage, AIMessage
from langgraph.graph import StateGraph, END


# ============================================================================
# 1. Swarm State & Handoff Schema Definition
# ============================================================================

class HandoffInstruction(BaseModel):
    """
    Structured Handoff Instruction defining transfer of control
    from one specialized agent to another.
    """
    target_agent: str = Field(..., description="Target specialized agent: 'hr', 'it', 'finance', 'compliance', or 'END'")
    reason: str = Field(..., description="Business rationale for handing off control")
    context_payload: Dict[str, Any] = Field(default_factory=dict, description="Payload data to merge into shared context")


class SwarmState(TypedDict, total=False):
    """
    Swarm Shared State structure maintaining both shared context
    and agent-isolated local states.
    """
    messages: Annotated[Sequence[BaseMessage], operator.add]
    active_agent: str
    shared_context: Dict[str, Any]
    agent_private_states: Dict[str, Dict[str, Any]]
    handoff_history: List[Dict[str, Any]]
    current_step: str


def handoff_to_agent(
    target_agent: str,
    context_payload: Optional[Dict[str, Any]] = None,
    reason: str = "Standard SOP Progression",
) -> HandoffInstruction:
    """
    Creates a standard HandoffInstruction to transfer conversational control.
    """
    valid_targets = {"hr", "it", "finance", "compliance", "END"}
    if target_agent not in valid_targets:
        raise ValueError(
            f"Invalid target_agent '{target_agent}'. Must be one of {valid_targets}"
        )
    return HandoffInstruction(
        target_agent=target_agent,
        reason=reason,
        context_payload=context_payload or {},
    )


# ============================================================================
# 2. Specialized Swarm Agent Nodes (New Employee Onboarding SOP Implementation)
# ============================================================================

def hr_swarm_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    HR Swarm Agent:
    Step 1 of Onboarding SOP: Registers employee profile, assigns employee ID,
    records private HR notes, updates shared_context, and triggers handoff to IT.
    """
    shared = dict(state.get("shared_context", {}))
    private = dict(state.get("agent_private_states", {}))
    history = list(state.get("handoff_history", []))

    # 1. Process Employee Registration
    emp_name = shared.get("candidate_name", "赵敏")
    dept = shared.get("department", "研发部")
    employee_id = f"EMP-2026-{abs(hash(emp_name)) % 9000 + 1000}"

    shared["employee_info"] = {
        "employee_id": employee_id,
        "name": emp_name,
        "department": dept,
        "title": "全栈研发专家",
        "rank": "P7",
        "join_date": "2026-09-01",
        "status": "PROFILE_CREATED",
    }

    # 2. Maintain Isolated Private HR State (Salary negotiation & background check confidential notes)
    private["hr"] = {
        "salary_range": "28k-32k",
        "bg_check_status": "PASSED_CLEAN",
        "internal_evaluator": "HR-VP",
    }

    # 3. Formulate Handoff to IT
    instruction = handoff_to_agent(
        target_agent="it",
        context_payload={"employee_id": employee_id, "department": dept},
        reason="Employee profile established. Handoff to IT Operations for workstation asset allocation.",
    )

    history.append({
        "from": "hr",
        "to": "it",
        "reason": instruction.reason,
        "payload": instruction.context_payload,
    })

    msg = AIMessage(
        content=f"【HR专职助手】新员工档案建立完毕，员工编号：{employee_id}。正在将控制权移交至 IT运维助手 进行办公资产调配。"
    )

    return {
        "messages": [msg],
        "active_agent": "it",
        "shared_context": shared,
        "agent_private_states": private,
        "handoff_history": history,
        "current_step": "hr_completed",
    }


def it_swarm_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    IT Swarm Agent:
    Step 2 of Onboarding SOP: Reads employee_info from shared context,
    allocates MacBook Pro and VPN access, records private IT logs,
    and triggers handoff to Finance for salary card binding.
    """
    shared = dict(state.get("shared_context", {}))
    private = dict(state.get("agent_private_states", {}))
    history = list(state.get("handoff_history", []))

    emp_info = shared.get("employee_info", {})
    employee_id = emp_info.get("employee_id", "EMP-UNKNOWN")

    # 1. Allocate IT Equipment & Systems
    allocated_assets = [
        {"item_name": "MacBook Pro 16", "sn": "SN-MBP-9812", "spec": "M3 Max / 36G"},
        {"item_name": "Dell 4K 27寸显示器", "sn": "SN-MON-3321", "spec": "U2723QE"},
    ]
    shared["it_assets"] = {
        "allocated_items": allocated_assets,
        "vpn_account": f"{emp_info.get('name', 'user')}@corp.vpn",
        "git_permissions": "repo:read-write",
        "asset_status": "PROVISIONED",
    }

    # 2. Maintain Isolated Private IT State (Device MAC address & internal VLAN switch port)
    private["it"] = {
        "vlan_tag": 1024,
        "mac_address": "3C:22:FB:A1:00:88",
        "radius_server": "10.0.1.254",
    }

    # 3. Formulate Handoff to Finance
    instruction = handoff_to_agent(
        target_agent="finance",
        context_payload={"employee_id": employee_id, "provisioned_devices": len(allocated_assets)},
        reason="IT assets and VPN permissions provisioned. Handoff to Finance for payroll card & budget binding.",
    )

    history.append({
        "from": "it",
        "to": "finance",
        "reason": instruction.reason,
        "payload": instruction.context_payload,
    })

    msg = AIMessage(
        content=f"【IT专职助手】已为员工 {employee_id} 完成 MacBook Pro 与办公外设分配，VPN权限已开通。正在移交至 财务助手 绑定薪资结算卡。"
    )

    return {
        "messages": [msg],
        "active_agent": "finance",
        "shared_context": shared,
        "agent_private_states": private,
        "handoff_history": history,
        "current_step": "it_completed",
    }


def finance_swarm_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Finance Swarm Agent:
    Step 3 of Onboarding SOP: Reads employee_info and it_assets,
    binds payroll bank account and department cost center budget,
    marks SOP completed and hands off to END.
    """
    shared = dict(state.get("shared_context", {}))
    private = dict(state.get("agent_private_states", {}))
    history = list(state.get("handoff_history", []))

    emp_info = shared.get("employee_info", {})
    employee_id = emp_info.get("employee_id", "EMP-UNKNOWN")

    # 1. Bind Payroll & Cost Center
    shared["finance_account"] = {
        "bank_name": "招商银行企业薪酬代发专户",
        "payroll_card_tail": "8899",
        "cost_center": f"CC-{emp_info.get('department', 'R&D')}",
        "tax_declaration_status": "REGISTERED",
        "sop_status": "COMPLETED",
    }

    # 2. Maintain Isolated Private Finance State (Company tax ID and internal banking routing code)
    private["finance"] = {
        "routing_code": "CMB-CORP-991",
        "tax_authority_code": "TX-0112-SH",
        "ledger_batch": "BATCH-20260901",
    }

    # 3. Terminate Swarm Handoff
    instruction = handoff_to_agent(
        target_agent="END",
        context_payload={"employee_id": employee_id, "onboarding_completed": True},
        reason="Payroll card and department budget account successfully bound. Onboarding SOP fully closed.",
    )

    history.append({
        "from": "finance",
        "to": "END",
        "reason": instruction.reason,
        "payload": instruction.context_payload,
    })

    msg = AIMessage(
        content=f"【财务专职助手】员工 {employee_id} 薪资代发卡与研发部成本中心账户绑定成功，税务登记完成。新员工入职 SOP 全流程闭环！"
    )

    return {
        "messages": [msg],
        "active_agent": "END",
        "shared_context": shared,
        "agent_private_states": private,
        "handoff_history": history,
        "current_step": "onboarding_sop_completed",
    }


# ============================================================================
# 3. Swarm Router & Workflow Construction
# ============================================================================

def swarm_router_condition(state: Dict[str, Any]) -> str:
    """
    Dynamic routing conditional edge based on active_agent in state.
    """
    active = state.get("active_agent", "hr")
    if active == "hr":
        return "hr"
    elif active == "it":
        return "it"
    elif active == "finance":
        return "finance"
    elif active == "compliance":
        return "compliance"
    return END


def build_swarm_workflow():
    """
    Constructs and compiles the multi-agent Swarm collaboration graph.
    Supports seamless peer-to-peer handoffs: HR -> IT -> Finance -> END.
    """
    workflow = StateGraph(SwarmState)

    # 1. Add Swarm Agent Nodes
    workflow.add_node("hr", hr_swarm_node)
    workflow.add_node("it", it_swarm_node)
    workflow.add_node("finance", finance_swarm_node)

    # 2. Set Entry Point
    workflow.set_entry_point("hr")

    # 3. Add Conditional Handoff Edges
    workflow.add_conditional_edges(
        "hr",
        swarm_router_condition,
        {"it": "it", "finance": "finance", END: END},
    )
    workflow.add_conditional_edges(
        "it",
        swarm_router_condition,
        {"finance": "finance", "hr": "hr", END: END},
    )
    workflow.add_conditional_edges(
        "finance",
        swarm_router_condition,
        {END: END, "hr": "hr", "it": "it"},
    )

    return workflow.compile()


swarm_workflow = build_swarm_workflow()
