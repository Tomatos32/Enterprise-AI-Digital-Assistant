"""Unit tests for Enterprise Knowledge Graph & Graph RAG Multi-hop Reasoning Engine (Issue-0022)."""

import pytest
from langchain_core.messages import HumanMessage

from backend.core.graph_rag import (
    EnterpriseKnowledgeGraph,
    GraphTriple,
    build_default_enterprise_graph,
    default_enterprise_kg,
)
from backend.graph.nodes.retrieve_node import retrieve_node
from backend.graph.state import AgentState


def test_graph_triple_model():
    """Test GraphTriple creation, formatting, and serialization."""
    triple = GraphTriple(
        subject="研发部",
        predicate="主管角色",
        object="技术总监",
        subject_type="Department",
        object_type="Role",
        metadata={"confidence": 0.98},
    )
    assert triple.to_tuple() == ("研发部", "主管角色", "技术总监")
    assert "【研发部】 --(主管角色)--> 【技术总监】" in triple.to_readable_sentence()
    assert triple.metadata["confidence"] == 0.98


def test_custom_kg_add_and_search():
    """Test custom EnterpriseKnowledgeGraph triple insertion and direct 1-hop search."""
    kg = EnterpriseKnowledgeGraph(name="CustomTestKG")
    kg.add_triple("运维部", "负责人", "运维总监", "Department", "Role")
    kg.add_triple("运维总监", "拥有权限", "生产集群发布", "Role", "Permission")

    triples = kg.get_all_triples()
    assert len(triples) == 2

    # Direct search on node
    direct_ops = kg.search_direct_triples("运维总监")
    assert len(direct_ops) == 2  # 1 incoming from 运维部, 1 outgoing to 生产集群发布
    subjects = {t.subject for t in direct_ops}
    objects = {t.object for t in direct_ops}
    assert "运维部" in subjects
    assert "生产集群发布" in objects


def test_multi_hop_traversal():
    """Test multi-hop topological path search up to 2 hops."""
    kg = EnterpriseKnowledgeGraph(name="TraversalKG")
    kg.add_triple("A", "to_b", "B")
    kg.add_triple("B", "to_c", "C")
    kg.add_triple("C", "to_d", "D")

    # 1-hop paths
    paths_1 = kg.multi_hop_search("A", max_hops=1)
    assert len(paths_1) == 1
    assert paths_1[0][0].object == "B"

    # 2-hop paths
    paths_2 = kg.multi_hop_search("A", max_hops=2)
    assert len(paths_2) == 2
    assert [t.object for t in paths_2[1]] == ["B", "C"]


def test_default_enterprise_kg_topology():
    """Test pre-populated enterprise knowledge graph topology and rule assertions."""
    kg = build_default_enterprise_graph()
    assert kg.graph.number_of_nodes() >= 15
    assert kg.graph.number_of_edges() >= 15

    # Check 研发部 & 技术总监 approval limits
    dev_triples = kg.search_direct_triples("技术总监")
    dev_predicates = {t.predicate: t.object for t in dev_triples}
    assert dev_predicates.get("采购单笔审批上限") == "¥20,000"
    assert dev_predicates.get("报销审批上限") == "¥10,000"

    # Check policy threshold & human-in-the-loop trigger
    threshold_triples = kg.search_direct_triples("¥5,000")
    triggers = [t.object for t in threshold_triples if t.predicate == "触发机制"]
    assert "Human-in-the-loop人机协同审批" in triggers


def test_query_graph_rag_reasoning():
    """Test natural language query entity extraction and multi-hop reasoning."""
    query = "请问研发部主管审批采购的上限是多少？另外MacBook Pro M3价格是多少？"
    result = default_enterprise_kg.query_graph_rag(query=query, max_hops=2)

    assert "研发部" in result["detected_entities"]
    assert "MacBook Pro M3" in result["detected_entities"]
    assert result["triples_count"] > 0
    assert len(result["formatted_graph_context"]) > 0
    assert "【研发部】" in result["formatted_graph_context"]
    assert "MacBook Pro M3" in result["formatted_graph_context"]


@pytest.mark.asyncio
async def test_retrieve_node_dual_path_integration():
    """Test LangGraph retrieve_node executing both Vector retrieval and Graph RAG."""
    query = "研发部主管可以审批多大金额的采购？"
    state: AgentState = {
        "messages": [HumanMessage(content=query)],
        "current_step": "init",
        "context": [],
        "user_id": "test_user_01",
        "approval_status": None,
        "approval_id": None,
        "tool_calls": [],
        "session_id": "session_graph_test",
    }

    res = await retrieve_node(state)
    assert res["current_step"] == "retrieved"
    contexts = res["context"]
    assert len(contexts) >= 1

    # Verify Graph RAG topological reasoning context was injected
    graph_context = next(
        (c for c in contexts if c.get("metadata", {}).get("type") == "graph_rag_topological_reasoning"),
        None,
    )
    assert graph_context is not None
    assert "【研发部】" in graph_context["content"]
    assert graph_context["metadata"]["source"] == "enterprise_knowledge_graph"
    assert "研发部" in graph_context["metadata"]["detected_entities"]
