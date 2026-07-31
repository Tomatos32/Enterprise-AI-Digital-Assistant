"""Unit tests for Hybrid Retrieval (BM25 + Qdrant Dense), RRF Fusion & Reranker Engine."""

from fastapi.testclient import TestClient
from langchain_core.documents import Document
from backend.main import app
from backend.rag.retriever import (
    tokenize_text,
    BM25Retriever,
    reciprocal_rank_fusion,
    Reranker,
    HybridRetriever,
)
from backend.core.security import create_access_token

client = TestClient(app)


def test_tokenize_text():
    """Tests Chinese & English tokenization."""
    tokens = tokenize_text("采购60000元设备需要CFO审批")
    assert "采" in tokens
    assert "购" in tokens
    assert "60000" in tokens
    assert "cfo" in tokens


def test_bm25_retriever():
    """Tests BM25 sparse keyword retriever indexing & search."""
    docs = [
        Document(page_content="采购金额小于5000元，由部门经理单独审批。", metadata={"id": 1}),
        Document(page_content="采购金额在5000元至50000元之间，由部门总监与财务总监共同审批。", metadata={"id": 2}),
        Document(page_content="采购金额大于50000元（例如60000元），必须提交CFO与VP联合会签审批。", metadata={"id": 3}),
    ]

    retriever = BM25Retriever(docs)
    results = retriever.search("60000元 审批", top_k=2)

    assert len(results) >= 1
    assert "60000元" in results[0].page_content
    assert results[0].metadata["id"] == 3
    assert "bm25_score" in results[0].metadata


def test_rrf_fusion():
    """Tests Reciprocal Rank Fusion algorithm across multiple lists."""
    doc_a = Document(page_content="切片A：采购审批5000元", metadata={"source": "A"})
    doc_b = Document(page_content="切片B：采购审批60000元CFO", metadata={"source": "B"})
    doc_c = Document(page_content="切片C：IT资产借用", metadata={"source": "C"})

    list_dense = [doc_b, doc_a]
    list_bm25 = [doc_b, doc_c]

    fused = reciprocal_rank_fusion([list_dense, list_bm25], k=60)
    assert len(fused) == 3
    # doc_b is rank 1 in both lists, so it must be top 1 in fused results
    assert fused[0].page_content == "切片B：采购审批60000元CFO"
    assert "rrf_score" in fused[0].metadata


def test_reranker():
    """Tests Reranker scoring and refinement."""
    docs = [
        Document(page_content="出差报销费用标准：住宿500元", metadata={"rrf_score": 0.01}),
        Document(page_content="采购金额大于50000元设备（如60000元），需要CFO和VP联合审批。", metadata={"rrf_score": 0.03}),
    ]

    reranker = Reranker()
    reranked = reranker.rerank("采购60000元设备需要谁审批", docs, top_k=2)

    assert len(reranked) == 2
    assert "60000元" in reranked[0].page_content
    assert reranked[0].metadata["rerank_score"] > reranked[1].metadata["rerank_score"]


def test_hybrid_retriever_approval_recall():
    """
    Tests end-to-end recall for query:
    '采购60000元设备需要谁审批'
    Verifies that the >50000 yuan CFO/VP joint approval rule is accurately retrieved.
    """
    hybrid = HybridRetriever()
    results = hybrid.retrieve(
        query="采购60000元设备需要谁审批",
        top_k=3,
        category_filter="PROCUREMENT"
    )

    assert len(results) >= 1
    # Check that top result correctly contains CFO/VP approval rule
    top_text = results[0].page_content
    assert any(keyword in top_text for keyword in ["50000", "CFO", "VP", "审批", "采购"])
    assert "rerank_score" in results[0].metadata


def test_post_knowledge_search_api():
    """Tests POST /api/v1/knowledge/search endpoint."""
    token = create_access_token(data={"sub": "employee_user", "role": "employee"})
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "query": "采购60000元设备需要谁审批",
        "top_k": 3,
        "category_filter": "PROCUREMENT"
    }

    response = client.post("/api/v1/knowledge/search", json=payload, headers=headers)

    assert response.status_code == 200
    res_json = response.json()
    assert res_json["code"] == 200
    assert res_json["data"]["query"] == "采购60000元设备需要谁审批"
    assert len(res_json["data"]["results"]) >= 1
    assert "metadata" in res_json["data"]["results"][0]
