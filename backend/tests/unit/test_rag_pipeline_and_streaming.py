"""Unit and Integration Tests for Real RAG Pipeline, LLM Factory,

Self-Correction Reflection, and Token Streaming.
"""

import pytest
from langchain_core.messages import HumanMessage

from backend.core.llm import get_chat_llm, get_llm_info
from backend.graph.nodes.generate_node import generate_node
from backend.graph.state import AgentState
from backend.graph.workflow import graph


def test_llm_factory_and_telemetry():
    """Validates LLM factory configuration and telemetry reporting."""
    info = get_llm_info()
    assert "provider" in info
    assert "model" in info
    assert "streaming" in info
    assert "active_engine" in info

    llm = get_chat_llm()
    assert llm is not None
    assert hasattr(llm, "ainvoke")
    assert hasattr(llm, "astream")


@pytest.mark.asyncio
async def test_local_enterprise_chat_model_domains():
    """Validates domain-specific knowledge synthesis in LocalEnterpriseChatModel."""
    llm = get_chat_llm()

    # 1. Travel expense query
    travel_res = await llm.ainvoke(
        [
            HumanMessage(
                content="请问一线城市出差差旅住宿标准与餐饮补贴是多少？参考制度：01_FINANCE_TRAVEL_POLICY.md"
            )
        ]
    )
    assert "[RAG Answer]" in travel_res.content or "[Chat Answer]" in travel_res.content

    # 2. General chat query
    chat_res = await llm.ainvoke([HumanMessage(content="你好，请问你可以帮我做什么？")])
    assert "[Chat Answer]" in chat_res.content


@pytest.mark.asyncio
async def test_generate_node_with_rag_context():
    """Validates generate_node synthesizes grounded answers with citations when context is present."""
    sample_context = [
        {
            "content": (
                "3. 采购金额与审批权限矩阵：\n"
                "采购金额在 50,000 元以上的重大采购，须由部门总监审核后报 CFO 与分管 VP 联合审批。"
            ),
            "metadata": {
                "filename": "03_FINANCE_PROCUREMENT_LIMITS.md",
                "source": "03_FINANCE_PROCUREMENT_LIMITS.md",
                "section_header": "采购审批矩阵",
                "rerank_score": 0.85,
            },
        }
    ]

    state: AgentState = {
        "messages": [HumanMessage(content="重大采购金额超过50000元需要谁来审批？")],
        "user_id": "u_test_rag",
        "session_id": "s_test_rag",
        "intent": "retrieve",
        "context": sample_context,
        "metadata": {},
    }

    result = await generate_node(state)
    assert "messages" in result
    assert result["current_step"] == "completed"
    answer = result["messages"][0].content
    assert "[RAG Answer]" in answer
    assert "50,000" in answer or "50000" in answer or "采购" in answer


@pytest.mark.asyncio
async def test_generate_node_self_correction_on_empty_context():
    """Validates generate_node triggers Self-Correction reflection when context is missing."""
    state: AgentState = {
        "messages": [HumanMessage(content="请问火星基地的飞船燃油补给标准是多少？")],
        "user_id": "u_test_reflect",
        "session_id": "s_test_reflect",
        "intent": "retrieve",
        "context": [],  # No relevant context found
        "metadata": {},
    }

    result = await generate_node(state)
    answer = result["messages"][0].content
    assert "[RAG Answer]" in answer
    # Must contain self-correction refusal or advice
    assert any(
        kw in answer
        for kw in ["未在知识库中检索到", "暂无直接命中", "自校验", "暂未", "建议", "合规"]
    )


@pytest.mark.asyncio
async def test_generate_node_tool_and_chat_branches():
    """Validates generate_node handling for tool output and chat branches."""
    # Tool execution branch
    tool_state: AgentState = {
        "messages": [HumanMessage(content="申请加急开通VPN权限")],
        "user_id": "u_tool",
        "session_id": "s_tool",
        "intent": "tool",
        "metadata": {"tool_executed": True, "tool_output": "工单 TICKET-8899 已成功创建并推送到运维工单池"},
    }
    tool_res = await generate_node(tool_state)
    tool_ans = tool_res["messages"][0].content
    assert "[Tool Answer]" in tool_ans
    assert "TICKET-8899" in tool_ans or "执行" in tool_ans

    # Conversational branch
    chat_state: AgentState = {
        "messages": [HumanMessage(content="早安，今天天气不错")],
        "user_id": "u_chat",
        "session_id": "s_chat",
        "intent": "chat",
        "metadata": {},
    }
    chat_res = await generate_node(chat_state)
    chat_ans = chat_res["messages"][0].content
    assert "[Chat Answer]" in chat_ans


@pytest.mark.asyncio
async def test_astream_events_token_streaming():
    """Validates that LangGraph astream_events successfully triggers on_chat_model_stream

    with realistic token chunks for real-time WebSocket pushing.
    """
    initial_state: AgentState = {
        "messages": [HumanMessage(content="查询考勤迟到宽限与病假规定")],
        "user_id": "u_stream_test",
        "session_id": "s_stream_test",
        "current_step": "init",
        "metadata": {},
    }
    config = {"configurable": {"thread_id": "thread_stream_verification"}}

    streamed_tokens = []
    has_chat_model_event = False

    async for event in graph.astream_events(initial_state, config=config, version="v2"):
        kind = event.get("event")
        if kind == "on_chat_model_stream":
            has_chat_model_event = True
            chunk = event.get("data", {}).get("chunk")
            if chunk and hasattr(chunk, "content") and chunk.content:
                streamed_tokens.append(chunk.content)

    assert has_chat_model_event is True
    assert len(streamed_tokens) > 0
    full_streamed_text = "".join(streamed_tokens)
    assert "[RAG Answer]" in full_streamed_text or "考勤" in full_streamed_text or "迟到" in full_streamed_text
