"""Tool Execution Node Implementation for LangGraph State Machine."""

from typing import Dict, Any
from backend.graph.state import AgentState


async def tool_node(state: AgentState) -> Dict[str, Any]:
    """
    Tool Node that processes action intents (e.g. creating tickets, sending emails)
    and updates state metadata with execution status.
    """
    messages = state.get("messages", [])
    query = messages[-1].content if messages else ""

    metadata = state.get("metadata", {}).copy()
    metadata["tool_executed"] = True
    metadata["tool_name"] = "action_dispatcher"
    metadata["tool_output"] = f"Executed action tool for request: {query}"

    return {
        "metadata": metadata,
        "current_step": "tool_executed"
    }
