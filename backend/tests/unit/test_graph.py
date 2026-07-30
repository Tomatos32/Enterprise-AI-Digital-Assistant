"""Unit Tests for LangGraph Workflow Execution & State Transitions."""

import pytest
from langchain_core.messages import HumanMessage
from backend.graph.workflow import graph
from backend.graph.state import AgentState


@pytest.mark.asyncio
async def test_langgraph_workflow_execution():
    """
    Tests the LangGraph state machine execution flow.
    """
    initial_state: AgentState = {
        "messages": [HumanMessage(content="Hello AI Harness")],
        "user_id": "test_user_001",
        "session_id": "session_abc123",
        "current_step": "init",
        "metadata": {}
    }
    
    config = {"configurable": {"thread_id": "thread_test_1"}}
    
    # Execute graph state transition
    result = await graph.ainvoke(initial_state, config=config)
    
    assert result is not None
    assert len(result["messages"]) == 2
    assert "Processed request - Hello AI Harness" in result["messages"][-1].content
    assert result["current_step"] == "completed"
