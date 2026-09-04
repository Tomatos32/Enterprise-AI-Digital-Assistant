"""Unit Tests for LangGraph Swarm Collaboration Protocol and Multi-hop Handoff."""

import pytest
from langchain_core.messages import HumanMessage

from backend.graph.swarm_router import (
    handoff_to_agent,
    HandoffInstruction,
    swarm_workflow,
)


# ============================================================================
# 1. Handoff Instruction & Validation Tests
# ============================================================================

def test_handoff_instruction_creation_and_validation():
    """验证 handoff_to_agent 契约生成与非法目标拦截."""
    instruction = handoff_to_agent(
        target_agent="it",
        context_payload={"employee_id": "EMP-2026-1001"},
        reason="Asset provisioning",
    )
    assert isinstance(instruction, HandoffInstruction)
    assert instruction.target_agent == "it"
    assert instruction.context_payload["employee_id"] == "EMP-2026-1001"
    assert instruction.reason == "Asset provisioning"

    # 非法 Agent 移交目标阻断
    with pytest.raises(ValueError) as exc_info:
        handoff_to_agent(target_agent="illegal_hacker_agent")
    assert "Invalid target_agent 'illegal_hacker_agent'" in str(exc_info.value)


# ============================================================================
# 2. Multi-hop Swarm Workflow End-to-End Onboarding SOP Tests
# ============================================================================

def test_swarm_onboarding_sop_multihop_handoff():
    """
    验证新员工入职 SOP 全流程 3 跳 Handoff 自动流转：
    HR (档案创建) ➔ IT (设备/VPN分配) ➔ Finance (薪资卡绑定) ➔ END
    """
    initial_state = {
        "messages": [HumanMessage(content="启动新员工入职 SOP 自动化办理流程")],
        "active_agent": "hr",
        "shared_context": {
            "candidate_name": "张无忌",
            "department": "人工智能前沿创新实验室",
        },
        "agent_private_states": {},
        "handoff_history": [],
    }

    # 执行完整的 Swarm 工作流
    result = swarm_workflow.invoke(initial_state)

    # 1. 验证最终状态与步骤
    assert result["current_step"] == "onboarding_sop_completed"
    assert result["active_agent"] == "END"

    # 2. 验证消息流转数量（各 Agent 均留下了交互日志）
    messages = result["messages"]
    assert len(messages) >= 3
    assert any("【HR专职助手】新员工档案建立完毕" in m.content for m in messages)
    assert any("【IT专职助手】已为员工" in m.content for m in messages)
    assert any("【财务专职助手】员工" in m.content for m in messages)

    # 3. 验证全局共享数据的一致性累积（Shared Context）
    shared = result["shared_context"]
    assert "employee_info" in shared
    emp_info = shared["employee_info"]
    assert emp_info["name"] == "张无忌"
    assert emp_info["department"] == "人工智能前沿创新实验室"
    assert emp_info["status"] == "PROFILE_CREATED"

    assert "it_assets" in shared
    it_assets = shared["it_assets"]
    assert it_assets["asset_status"] == "PROVISIONED"
    assert len(it_assets["allocated_items"]) == 2

    assert "finance_account" in shared
    fin_acc = shared["finance_account"]
    assert fin_acc["sop_status"] == "COMPLETED"
    assert "招商银行" in fin_acc["bank_name"]

    # 4. 验证 Handoff 审计轨迹（Handoff History 完整包含 3 跳）
    history = result["handoff_history"]
    assert len(history) == 3
    assert history[0]["from"] == "hr" and history[0]["to"] == "it"
    assert history[1]["from"] == "it" and history[1]["to"] == "finance"
    assert history[2]["from"] == "finance" and history[2]["to"] == "END"


# ============================================================================
# 3. Agent Private State Isolation Tests
# ============================================================================

def test_agent_private_state_isolation():
    """验证各专职 Agent 内部隐私状态完全隔离，互不干扰与泄露."""
    initial_state = {
        "messages": [HumanMessage(content="入职流程")],
        "active_agent": "hr",
        "shared_context": {
            "candidate_name": "周芷若",
            "department": "技术支持部",
        },
        "agent_private_states": {},
        "handoff_history": [],
    }

    result = swarm_workflow.invoke(initial_state)
    private = result["agent_private_states"]

    # 验证 HR 私有薪酬评估与背调数据被安全隔离在 private['hr']
    assert "hr" in private
    assert private["hr"]["bg_check_status"] == "PASSED_CLEAN"
    assert "vlan_tag" not in private["hr"]  # 无法看到 IT 的私有字段

    # 验证 IT 私有网络配置数据被安全隔离在 private['it']
    assert "it" in private
    assert private["it"]["vlan_tag"] == 1024
    assert "salary_range" not in private["it"]  # IT 看不到 HR 的薪资私有字段

    # 验证 Finance 私有税务与路由码数据被隔离在 private['finance']
    assert "finance" in private
    assert private["finance"]["tax_authority_code"] == "TX-0112-SH"
    assert "mac_address" not in private["finance"]  # 财务看不到 IT 的 MAC 地址
