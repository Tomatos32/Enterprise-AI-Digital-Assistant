"""Chatbot Node Implementation for LangGraph State Machine."""

from langchain_core.messages import AIMessage
from backend.graph.state import AgentState


async def chatbot_node(state: AgentState) -> dict:
    """
    Core Chatbot Node that processes state messages and returns updated state updates.
    """
    messages = state.get("messages", [])
    last_message = messages[-1].content if messages else "Hello"
    
    # Process or echo response (Scaffold Node)
    response_content = f"[AI Assistant]: Processed request - {last_message}"
    
    return {
        "messages": [AIMessage(content=response_content)],
        "current_step": "completed"
    }
