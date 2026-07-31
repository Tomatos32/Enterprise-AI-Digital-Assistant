"""Unit tests for Qdrant Vector Store and Knowledge File Upload API."""

from pathlib import Path
from fastapi.testclient import TestClient
from langchain_core.documents import Document
from qdrant_client import QdrantClient

from backend.main import app
from backend.rag.vector_store import (
    get_embedding,
    init_qdrant_collection,
    upsert_documents,
    search_similar_documents,
)
from backend.core.security import create_access_token

client = TestClient(app)


def test_embedding_generation():
    """Tests 1024-dim embedding generation and normalization."""
    vec1 = get_embedding("企业采购审批流程SOP", dim=1024)
    vec2 = get_embedding("企业采购审批流程SOP", dim=1024)
    vec3 = get_embedding("IT资产借用与管理规范", dim=1024)

    assert len(vec1) == 1024
    assert vec1 == vec2  # Deterministic
    assert vec1 != vec3  # Content difference


def test_init_qdrant_collection_memory():
    """Tests initializing collection in memory Qdrant client."""
    q_client = QdrantClient(":memory:")
    col_name = "test_enterprise_knowledge"
    
    res = init_qdrant_collection(collection_name=col_name, vector_size=1024, client=q_client)
    assert res is True

    collections = [c.name for c in q_client.get_collections().collections]
    assert col_name in collections


def test_upsert_and_search_documents():
    """Tests upserting Document objects and performing similarity search."""
    q_client = QdrantClient(":memory:")
    col_name = "test_search_collection"

    docs = [
        Document(
            page_content="采购金额在5000元以内的办公用品，部门经理可直接一键审批。",
            metadata={"category": "PROCUREMENT", "sop_code": "PROC-001"}
        ),
        Document(
            page_content="超过50000元的重大采购，必须提交CFO和VP联合会签审批。",
            metadata={"category": "PROCUREMENT", "sop_code": "PROC-002"}
        ),
        Document(
            page_content="员工出差住宿标准：一线城市最高补贴500元/天，二线城市最高350元/天。",
            metadata={"category": "FINANCE", "sop_code": "FIN-001"}
        )
    ]

    indexed_count = upsert_documents(docs=docs, collection_name=col_name, client=q_client)
    assert indexed_count == 3

    # Perform similarity search
    results = search_similar_documents(
        query="采购 50000元 审批",
        top_k=2,
        collection_name=col_name,
        client=q_client
    )

    assert len(results) == 2
    assert "page_content" not in results[0].metadata
    assert "category" in results[0].metadata
    assert "score" in results[0].metadata


def test_knowledge_upload_api(tmp_path):
    """Tests POST /api/v1/knowledge/upload with file upload."""
    token = create_access_token(data={"sub": "admin_user", "role": "admin"})
    headers = {"Authorization": f"Bearer {token}"}

    test_file_path = tmp_path / "05_TEST_PROCUREMENT_POLICY.md"
    test_file_path.write_text("# 临时测试采购制度\n\n采购超过10000元需要提交招投标委员会。", encoding="utf-8")

    with open(test_file_path, "rb") as f:
        response = client.post(
            "/api/v1/knowledge/upload",
            files={"file": ("05_TEST_PROCUREMENT_POLICY.md", f, "text/markdown")},
            data={"category": "PROCUREMENT"},
            headers=headers
        )

    assert response.status_code == 200
    res_json = response.json()
    assert res_json["code"] == 200
    assert res_json["data"]["filename"] == "05_TEST_PROCUREMENT_POLICY.md"
    assert res_json["data"]["chunks_indexed"] >= 1

    saved_file = Path("backend/data/05_TEST_PROCUREMENT_POLICY.md")
    assert saved_file.exists()


def test_knowledge_search_api():
    """Tests GET /api/v1/knowledge/search API endpoint."""
    token = create_access_token(data={"sub": "employee_user", "role": "employee"})
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get(
        "/api/v1/knowledge/search",
        params={"query": "采购 审批", "top_k": 3},
        headers=headers
    )

    assert response.status_code == 200
    res_json = response.json()
    assert res_json["code"] == 200
    assert "results" in res_json["data"]
