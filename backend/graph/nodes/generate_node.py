"""Response Generation Node Implementation for LangGraph State Machine."""

from typing import Dict, Any
from langchain_core.messages import AIMessage
from backend.graph.state import AgentState


async def generate_node(state: AgentState) -> Dict[str, Any]:
    """
    Response Generation Node that synthesizes state messages, retrieved context,
    or tool execution status to produce the final AI assistant response.
    """
    messages = state.get("messages", [])
    last_query = messages[-1].content if messages else "Hello"
    context = state.get("context", [])
    intent = state.get("intent", "chat")
    metadata = state.get("metadata", {})

    if intent == "retrieve" and context:
        sources = [doc.get("metadata", {}).get("filename", "Doc") for doc in context[:2]]
        snippets = "\n---\n".join([doc.get("content", "")[:150] for doc in context[:2]])
        answer = (
            f"[RAG Answer]: Based on corporate knowledge base ({', '.join(sources)}):\n\n"
            f"{snippets}\n\n"
            f"(Targeting query: '{last_query}')"
        )
    elif intent == "tool" and metadata.get("tool_executed"):
        tool_output = metadata.get("tool_output", "Success")
        answer = f"[Tool Answer]: {tool_output}"
    else:
        answer = f"[Chat Answer]: Hello! I have processed your message: '{last_query}'"

    return {
        "messages": [AIMessage(content=answer)],
        "current_step": "completed"
    }
