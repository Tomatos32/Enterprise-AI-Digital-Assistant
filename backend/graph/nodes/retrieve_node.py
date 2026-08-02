"""Knowledge Retrieval Node Implementation for LangGraph State Machine."""

from typing import Dict, Any, List
from pathlib import Path
from backend.graph.state import AgentState
from backend.rag.retriever import HybridRetriever


async def retrieve_node(state: AgentState) -> Dict[str, Any]:
    """
    Retrieval Node that calls HybridRetriever to fetch relevant knowledge slices
    from sample_kb and writes the results into state['context'].
    """
    messages = state.get("messages", [])
    query = messages[-1].content if messages else ""

    # Path to sample_kb
    product_root = Path(__file__).resolve().parent.parent.parent.parent
    sample_kb_dir = product_root / "docs" / "sample_kb"

    retriever = HybridRetriever(sample_kb_dir=sample_kb_dir)
    docs = retriever.retrieve(query=query, top_k=3)

    formatted_context: List[Dict[str, Any]] = [
        {
            "content": doc.page_content,
            "metadata": doc.metadata
        }
        for doc in docs
    ]

    return {
        "context": formatted_context,
        "current_step": "retrieved"
    }
