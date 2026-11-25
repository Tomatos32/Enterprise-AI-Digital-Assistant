"""Knowledge Retrieval Node Implementation for LangGraph State Machine.

Integrates dual-path retrieval with dynamic RBAC & Multi-tenancy isolation:
1. Vector / Hybrid document chunk retrieval (Qdrant & BM25 via HybridRetriever with RBAC security filter).
2. Enterprise Knowledge Graph (Graph RAG) topological multi-hop reasoning.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List

from langchain_core.messages import BaseMessage

from backend.core.graph_rag import default_enterprise_kg
from backend.graph.state import AgentState
from backend.rag.query_rewriter import get_query_rewriter
from backend.rag.retriever import get_hybrid_retriever

logger = logging.getLogger(__name__)


async def retrieve_node(state: AgentState) -> Dict[str, Any]:
    """Retrieval Node that performs dual-path retrieval (Vector + Graph RAG)

    enforcing dynamic RBAC and multi-tenancy security from state metadata,
    and writes the fused results into state['context'].
    """
    messages: List[BaseMessage] = list(state.get("messages", []))
    raw_query = messages[-1].content if messages else ""
    query = raw_query if isinstance(raw_query, str) else str(raw_query)

    # Extract user RBAC and tenant credentials from state or metadata
    metadata = dict(state.get("metadata", {}) or {})
    normalized = str(metadata.get("normalized_query") or "").strip()
    if normalized:
        query = normalized
    user_info = metadata.get("user") or {}

    tenant_id = user_info.get("tenant_id") or metadata.get("tenant_id") or "default"
    user_department = user_info.get("department") or metadata.get("department")
    clearance_level = user_info.get("clearance_level") or metadata.get("clearance_level", 1)

    # 0. Query Rewriting & Sub-Query Decomposition
    history_messages = messages[:-1] if len(messages) > 1 else []
    rewriter = get_query_rewriter()
    rewritten = rewriter.rewrite(query=query, history=history_messages)

    # 1. Path to sample_kb for Vector / Hybrid Retriever
    product_root = Path(__file__).resolve().parent.parent.parent.parent
    sample_kb_dir = product_root / "docs" / "sample_kb"

    from backend.core.runtime_config import get_runtime_config

    runtime_cfg = get_runtime_config()
    retriever = get_hybrid_retriever(sample_kb_dir=sample_kb_dir)
    docs = retriever.retrieve(
        query=rewritten.standalone_query,
        top_k=runtime_cfg.rag_top_k,
        min_score=runtime_cfg.rag_min_score,
        tenant_id=tenant_id,
        user_department=user_department,
        clearance_level=clearance_level,
        sub_queries=rewritten.sub_queries,
        primary_domain=rewritten.primary_domain,
    )

    formatted_context: List[Dict[str, Any]] = [
        {
            "content": doc.page_content,
            "metadata": doc.metadata,
        }
        for doc in docs
    ]

    # 2. Graph RAG Topological Knowledge Graph Multi-hop Reasoning
    try:
        graph_result = default_enterprise_kg.query_graph_rag(query=query, max_hops=2)
        if graph_result.get("triples_count", 0) > 0:
            graph_doc = {
                "content": graph_result.get("formatted_graph_context", ""),
                "metadata": {
                    "source": "enterprise_knowledge_graph",
                    "type": "graph_rag_topological_reasoning",
                    "detected_entities": graph_result.get("detected_entities", []),
                    "triples_count": graph_result.get("triples_count", 0),
                    "multi_hop_chains": graph_result.get("multi_hop_chains", []),
                },
            }
            # Prepend graph topological context as high-priority structural knowledge
            formatted_context.insert(0, graph_doc)
            logger.info(
                f"[RetrieveNode] Injected Graph RAG context with "
                f"{graph_result['triples_count']} triples and "
                f"{len(graph_result['multi_hop_chains'])} multi-hop paths (Tenant={tenant_id}, Dept={user_department}, Clearance={clearance_level})."
            )
    except Exception as e:
        logger.warning(f"[RetrieveNode] Graph RAG reasoning query failed: {e}")

    return {
        "context": formatted_context,
        "current_step": "retrieved",
    }
