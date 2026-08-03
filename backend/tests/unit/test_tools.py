"""Unit Tests for ToolRegistry, 5 Core Enterprise Tools, and LangGraph Tool Node Integration."""

import pytest
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from backend.tools import registry
from backend.tools.impl import (
    query_employee,
    query_inventory,
    create_ticket,
    create_purchase,
    send_email,
)
from backend.graph.nodes.tool_node import tool_node
from backend.graph.workflow import graph
from backend.graph.state import AgentState


def test_tool_registry_openai_schema_export():
    """Tests ToolRegistry schema generation compliant with OpenAI / Qwen specs."""
    tools_schema = registry.get_openai_tools()
    assert isinstance(tools_schema, list)
    assert len(tools_schema) >= 5

    tool_names = {t["function"]["name"] for t in tools_schema}
    assert "query_employee" in tool_names
    assert "query_inventory" in tool_names
    assert "create_ticket" in tool_names
    assert "create_purchase" in tool_names
    assert "send_email" in tool_names

    for item in tools_schema:
        assert item["type"] == "function"
        fn = item["function"]
        assert "name" in fn
        assert "description" in fn
        assert "parameters" in fn
        assert fn["parameters"]["type"] == "object"


def test_query_employee_tool():
    """Tests query_employee tool logic."""
    res = query_employee("张伟")
    assert res["status"] == "SUCCESS"
    assert res["count"] >= 1
    emp = res["data"][0]
    assert emp["name"] == "张伟"
    assert emp["department"] == "IT运维部"
    assert emp["rank"] == "P6"

    not_found = query_employee("不存在的神秘员工")
    assert not_found["status"] == "NOT_FOUND"
    assert not_found["count"] == 0


def test_query_inventory_tool():
    """Tests query_inventory tool logic."""
    res = query_inventory("MacBook")
    assert res["status"] == "SUCCESS"
    assert res["count"] >= 1
    assert res["data"][0]["unit_price"] == 22999

    res_screen = query_inventory("显示器")
    assert res_screen["status"] == "SUCCESS"
    assert res_screen["data"][0]["stock"] == 28


def test_create_ticket_tool():
    """Tests create_ticket tool SLA and ID generation."""
    res_p1 = create_ticket(title="核心网络崩溃", description="交换机宕机", priority="P1")
    assert res_p1["status"] == "SUCCESS"
    assert res_p1["ticket_id"].startswith("TICK-")
    assert res_p1["priority"] == "P1"
    assert res_p1["response_sla"] == "< 15 分钟"

    res_p3 = create_ticket(title="密码重置", description="重置域账号密码", priority="P3")
    assert res_p3["response_sla"] == "< 4 小时"


def test_create_purchase_tool_approval_thresholds():
    """Tests create_purchase tool threshold approval logic (SOP DOC-PROC-2026-002)."""
    # 1. <= 5000 RMB -> Auto Approved
    res_small = create_purchase(item_name="显示器", quantity=1, unit_price=3499.0, department="IT运维部")
    assert res_small["status"] == "SUCCESS"
    assert res_small["total_price"] == 3499.0
    assert res_small["approval_status"] == "AUTO_APPROVED"

    # 2. 5000 < price <= 50000 -> Pending Supervisor
    res_medium = create_purchase(item_name="MacBook Pro", quantity=2, unit_price=22999.0, department="研发部")
    assert res_medium["total_price"] == 45998.0
    assert res_medium["approval_status"] == "PENDING_SUPERVISOR_APPROVAL"

    # 3. > 200000 -> Pending Board
    res_large = create_purchase(item_name="IDC 服务器", quantity=5, unit_price=85000.0, department="IT运维部")
    assert res_large["total_price"] == 425000.0
    assert res_large["approval_status"] == "PENDING_BOARD_APPROVAL"


def test_send_email_tool():
    """Tests send_email tool logic."""
    res = send_email(to_email="zhangwei@company.com", subject="测试邮件", body="此为测试邮件正文")
    assert res["status"] == "SENT"
    assert res["message_id"].startswith("MSG-EML-")

    err = send_email(to_email="invalid_email_str", subject="错误测试", body="正文")
    assert err["status"] == "ERROR"


@pytest.mark.asyncio
async def test_tool_node_executes_tool_calls_and_returns_tool_messages():
    """Tests LangGraph tool_node handling tool_calls and returning ToolMessage."""
    ai_msg = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "create_ticket",
                "args": {"title": "紧急P1网络中断", "description": "核心网关拥堵", "priority": "P1"},
                "id": "call_ticket_9918"
            }
        ]
    )
    state: AgentState = {
        "messages": [ai_msg],
        "user_id": "u_tool",
        "session_id": "s_tool",
        "metadata": {}
    }

    result = await tool_node(state)
    assert result["current_step"] == "tool_executed"
    assert len(result["messages"]) == 1

    tool_msg = result["messages"][0]
    assert isinstance(tool_msg, ToolMessage)
    assert tool_msg.tool_call_id == "call_ticket_9918"
    assert tool_msg.name == "create_ticket"
    assert "TICK-" in tool_msg.content


@pytest.mark.asyncio
async def test_langgraph_full_tool_execution_trajectory():
    """Tests full LangGraph execution for tool queries: START -> router -> tool -> generate -> END."""
    initial_state: AgentState = {
        "messages": [HumanMessage(content="帮我创建工单，申请设备硬件故障排查")],
        "user_id": "u_flow",
        "session_id": "s_flow",
        "current_step": "init",
        "metadata": {}
    }
    config = {"configurable": {"thread_id": "thread_tool_full"}}

    result = await graph.ainvoke(initial_state, config=config)

    assert result is not None
    assert result["intent"] == "tool"
    assert result["metadata"].get("tool_executed") is True

    # State messages should contain HumanMessage, ToolMessage, and AIMessage
    has_tool_msg = any(isinstance(m, ToolMessage) for m in result["messages"])
    assert has_tool_msg is True
    assert "[Tool Answer]" in result["messages"][-1].content
