"""LangGraph StateGraph Workflow Construction & MemorySaver Checkpointer Integration."""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from backend.graph.state import AgentState
from backend.graph.nodes import (
    router_node,
    retrieve_node,
    tool_node,
    approval_node,
    generate_node,
)


def route_intent(state: AgentState) -> str:
    """
    Conditional routing edge function that inspects state['intent']
    and returns the target node name: 'retrieve', 'tool', 'approval', or 'generate'.
    """
    intent = state.get("intent", "chat")
    if intent == "retrieve":
        return "retrieve"
    elif intent == "tool":
        return "tool"
    elif intent == "approval":
        return "approval"
    else:
        return "generate"


def build_graph():
    """
    Constructs and compiles the StateGraph for Enterprise AI Agent.
    Topology: START -> router -> (retrieve / tool / approval / generate) -> generate -> END
    """
    builder = StateGraph(AgentState)

    # 1. Add Nodes
    builder.add_node("router", router_node)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("tool", tool_node)
    builder.add_node("approval", approval_node)
    builder.add_node("generate", generate_node)

    # 2. Set Entry Point and Conditional Edges
    builder.set_entry_point("router")

    builder.add_conditional_edges(
        "router",
        route_intent,
        {
            "retrieve": "retrieve",
            "tool": "tool",
            "approval": "approval",
            "generate": "generate",
        },
    )

    # 3. Direct Edges
    builder.add_edge("retrieve", "generate")
    builder.add_edge("tool", "generate")
    builder.add_edge("approval", "generate")
    builder.add_edge("generate", END)

    # 4. Add Checkpointer for Human-In-The-Loop & Memory Thread Persistence
    checkpointer = MemorySaver()
    compiled_graph = builder.compile(checkpointer=checkpointer)

    return compiled_graph


# Export default graph instance for LangGraph CLI & FastAPI integration
graph = build_graph()
