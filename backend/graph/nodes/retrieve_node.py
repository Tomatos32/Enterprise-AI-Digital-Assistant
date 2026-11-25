"""Knowledge Retrieval Node Implementation for LangGraph State Machine.

Integrates dual-path retrieval with hybrid multi-turn query rewriting and dynamic RBAC isolation:
1. Context-Aware Hybrid Query Rewriting (pronoun + implicit ellipsis + multi-domain soft weights).
2. Vector / Hybrid document chunk retrieval (Qdrant & BM25 via HybridRetriever with RBAC security filter).
3. Enterprise Knowledge Graph (Graph RAG) topological multi-hop reasoning consuming standalone rewritten query.
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
    """Retrieval Node executing hybrid multi-turn query rewriting and dual-path retrieval (Vector + Graph RAG)."""
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
    data_source = metadata.get("data_source_id") or metadata.get("data_source")

    # 0. Multi-Turn Contextual Query Rewriting & Multi-Domain Decomposition
    history_messages = messages[:-1] if len(messages) > 1 else []
    rewriter = get_query_rewriter()
    rewritten = await rewriter.arewrite(
        query=query,
        history=history_messages,
        data_source=str(data_source) if data_source else None,
    )

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
        domains=rewritten.domains,
        domain_weights=rewritten.domain_weights,
    )

    formatted_context: List[Dict[str, Any]] = [
        {
            "content": doc.page_content,
            "metadata": doc.metadata,
        }
        for doc in docs
    ]

    # 2. Graph RAG Topological Knowledge Graph Multi-hop Reasoning using rewritten standalone_query
    try:
        graph_query = rewritten.standalone_query or query
        graph_result = default_enterprise_kg.query_graph_rag(query=graph_query, max_hops=2)
        if graph_result.get("triples_count", 0) == 0 and graph_query != query:
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
                    "graph_query": graph_result.get("query", graph_query),
                },
            }
            # Prepend graph topological context as high-priority structural knowledge
            formatted_context.insert(0, graph_doc)
            logger.info(
                "[RetrieveNode] Injected Graph RAG context with %d triples and %d multi-hop paths "
                "(Query='%s', Tenant=%s, Dept=%s, Clearance=%s).",
                graph_result["triples_count"],
                len(graph_result["multi_hop_chains"]),
                graph_result.get("query", graph_query),
                tenant_id,
                user_department,
                clearance_level,
            )
    except Exception as e:
        logger.warning("[RetrieveNode] Graph RAG reasoning query failed: %s", e)

    # Record server-side rewrite diagnostics without clobbering existing metadata keys
    updated_metadata = {
        **metadata,
        "rewritten_query": rewritten.standalone_query,
        "sub_queries": list(rewritten.sub_queries),
        "detected_domains": list(rewritten.domains),
        "domain_weights": dict(rewritten.domain_weights),
        "rewrite_method": rewritten.rewrite_method,
        "coreference_resolved": rewritten.coreference_resolved,
        "anchor_topic": rewritten.anchor_topic,
    }

    return {
        "context": formatted_context,
        "current_step": "retrieved",
        "metadata": updated_metadata,
    }
