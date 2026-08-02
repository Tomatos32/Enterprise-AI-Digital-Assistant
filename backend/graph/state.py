"""AgentState Schema Definition following LangGraph & Pydantic Specifications."""

from typing import Annotated, Sequence, TypedDict, Any
from langchain_core.messages import BaseMessage
import operator


class AgentState(TypedDict, total=False):
    """
    State dictionary representing the current state of an AI Agent thread.
    Uses operator.add to append new messages to conversation history.
    """
    messages: Annotated[Sequence[BaseMessage], operator.add]
    user_id: str
    session_id: str
    current_step: str
    metadata: dict[str, Any]
    intent: str
    context: list[dict[str, Any]]
