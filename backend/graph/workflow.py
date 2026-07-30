"""LangGraph StateGraph Workflow Construction & MemorySaver Checkpointer Integration."""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from backend.graph.state import AgentState
from backend.graph.nodes.chatbot import chatbot_node


def build_graph():
    """
    Constructs and compiles the StateGraph for Enterprise AI Agent.
    """
    builder = StateGraph(AgentState)
    
    # 1. Add Nodes
    builder.add_node("chatbot", chatbot_node)
    
    # 2. Set Entry Point and Edges
    builder.set_entry_point("chatbot")
    builder.add_edge("chatbot", END)
    
    # 3. Add Checkpointer for Human-In-The-Loop & Memory Thread Persistence
    checkpointer = MemorySaver()
    compiled_graph = builder.compile(checkpointer=checkpointer)
    
    return compiled_graph


# Export default graph instance for LangGraph CLI & FastAPI integration
graph = build_graph()
