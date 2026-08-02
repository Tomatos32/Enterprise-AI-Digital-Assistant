"""Unit Tests for LangGraph Node Topology & Multi-Branch Intent Routing Engine."""

import pytest
from langchain_core.messages import HumanMessage
from backend.graph.state import AgentState
from backend.graph.nodes import router_node, retrieve_node
from backend.graph.workflow import graph


@pytest.mark.asyncio
async def test_router_node_classification():
    """Tests intent classification for retrieve, tool, and chat queries."""
    # Retrieve intent
    retrieve_state: AgentState = {
        "messages": [HumanMessage(content="请问公司年假规章和考勤打卡制度是怎样的？")],
        "user_id": "u1",
        "session_id": "s1"
    }
    r1 = await router_node(retrieve_state)
    assert r1["intent"] == "retrieve"

    # Tool intent
    tool_state: AgentState = {
        "messages": [HumanMessage(content="请帮我创建工单通知运维研发")],
        "user_id": "u2",
        "session_id": "s2"
    }
    r2 = await router_node(tool_state)
    assert r2["intent"] == "tool"

    # Chat intent
    chat_state: AgentState = {
        "messages": [HumanMessage(content="你好，你是谁？")],
        "user_id": "u3",
        "session_id": "s3"
    }
    r3 = await router_node(chat_state)
    assert r3["intent"] == "chat"


@pytest.mark.asyncio
async def test_retrieve_node_context_population():
    """Tests that retrieve_node populates knowledge context into state."""
    state: AgentState = {
        "messages": [HumanMessage(content="财务差旅报销标准及住宿上限")],
        "user_id": "u1",
        "session_id": "s1"
    }
    res = await retrieve_node(state)
    assert "context" in res
    assert len(res["context"]) > 0
    assert res["current_step"] == "retrieved"


@pytest.mark.asyncio
async def test_retrieve_branch_trajectory():
    """Tests full execution trajectory for Retrieve intent branch: START -> router -> retrieve -> generate -> END."""
    initial_state: AgentState = {
        "messages": [HumanMessage(content="查询采购与审批SOP图文版金额门禁规定")],
        "user_id": "u_rag",
        "session_id": "s_rag",
        "current_step": "init",
        "metadata": {}
    }
    config = {"configurable": {"thread_id": "thread_retrieve_branch"}}

    result = await graph.ainvoke(initial_state, config=config)

    assert result is not None
    assert result["intent"] == "retrieve"
    assert "context" in result
    assert len(result["context"]) > 0
    assert result["current_step"] == "completed"
    last_msg = result["messages"][-1].content
    assert "[RAG Answer]" in last_msg


@pytest.mark.asyncio
async def test_tool_branch_trajectory():
    """Tests full execution trajectory for Tool intent branch: START -> router -> tool -> generate -> END."""
    initial_state: AgentState = {
        "messages": [HumanMessage(content="帮忙创建工单，提交硬件申请发邮件通知")],
        "user_id": "u_tool",
        "session_id": "s_tool",
        "current_step": "init",
        "metadata": {}
    }
    config = {"configurable": {"thread_id": "thread_tool_branch"}}

    result = await graph.ainvoke(initial_state, config=config)

    assert result is not None
    assert result["intent"] == "tool"
    assert result["metadata"].get("tool_executed") is True
    assert result["current_step"] == "completed"
    last_msg = result["messages"][-1].content
    assert "[Tool Answer]" in last_msg


@pytest.mark.asyncio
async def test_chat_branch_trajectory():
    """Tests full execution trajectory for Chat intent branch: START -> router -> generate -> END."""
    initial_state: AgentState = {
        "messages": [HumanMessage(content="你好，很高兴见到你")],
        "user_id": "u_chat",
        "session_id": "s_chat",
        "current_step": "init",
        "metadata": {}
    }
    config = {"configurable": {"thread_id": "thread_chat_branch"}}

    result = await graph.ainvoke(initial_state, config=config)

    assert result is not None
    assert result["intent"] == "chat"
    assert result["current_step"] == "completed"
    last_msg = result["messages"][-1].content
    assert "[Chat Answer]" in last_msg
