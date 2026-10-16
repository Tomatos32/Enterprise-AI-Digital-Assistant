"""Unit and Integration Tests for Real Embedding Engine, Document Splitter,

Qdrant Persistence, and Knowledge Ingestion Pipeline.
"""

from pathlib import Path
from fastapi.testclient import TestClient
from langchain_core.documents import Document
from qdrant_client import QdrantClient

from backend.core.security import create_access_token
from backend.main import app
from backend.rag.embeddings import (
    LocalSemanticEngine,
    get_embedding,
    get_embedding_engine_info,
    get_embeddings_batch,
)
from backend.rag.splitter import split_documents, split_text
from backend.rag.vector_store import (
    get_qdrant_client,
    get_qdrant_info,
    search_similar_documents,
    upsert_documents,
)
from backend.scripts.ingest_knowledge import ingest_knowledge_base

client = TestClient(app)


def test_local_semantic_embedding_engine():
    """Validates LocalSemanticEngine output dimensions, normalization and semantic cosine discrimination."""
    engine = LocalSemanticEngine(default_dim=1024)
    assert engine.provider_name == "local_semantic"
    assert engine.default_dimension == 1024

    text1 = "重大采购审批权限矩阵：超过50000元需CFO与VP联合审批。"
    text2 = "采购金额在5万元以上的重大采购审批流程规范。"
    text3 = "员工年度带薪病假额度为每年5天，须提供二级甲等医院证明。"

    v1 = engine.embed_text(text1)
    v2 = engine.embed_text(text2)
    v3 = engine.embed_text(text3)

    assert len(v1) == 1024
    assert len(v2) == 1024
    assert len(v3) == 1024

    # Check normalization
    norm1 = sum(x * x for x in v1) ** 0.5
    assert abs(norm1 - 1.0) < 1e-4

    # Cosine similarities
    sim_related = sum(a * b for a, b in zip(v1, v2))
    sim_unrelated = sum(a * b for a, b in zip(v1, v3))

    # Related texts must have strictly higher cosine similarity than unrelated texts
    assert sim_related > sim_unrelated
    assert sim_related > 0.20
    assert sim_unrelated < 0.10
    assert sim_related > sim_unrelated + 0.15


def test_batch_embeddings_and_telemetry():
    """Validates batch embeddings and engine info retrieval."""
    texts = ["企业年金规章", "差旅报销餐饮标准", "信息安全事件上报流程"]
    batch = get_embeddings_batch(texts, dim=1024)
    assert len(batch) == 3
    assert all(len(v) == 1024 for v in batch)

    single = get_embedding(texts[0], dim=1024)
    assert batch[0] == single

    info = get_embedding_engine_info()
    assert "provider" in info
    assert "model" in info
    assert info["dimension"] == 1024
    assert info["status"] == "ready"


def test_document_splitter_logic():
    """Validates recursive semantic text and document chunking."""
    sample_text = (
        "# 财务报销制度\n\n"
        "## 1. 差旅标准\n"
        "一线城市住宿补贴标准为500元/天，二线城市住宿补贴标准为350元/天。\n\n"
        "## 2. 餐饮标准\n"
        "出差期间餐饮补贴统一为100元/天，凭有效增值税普通发票实报实销。\n\n"
        "## 3. 交通报销\n"
        "市内交通凭打车发票或公共交通票据据实报销，单次市内出租车超过200元需主管特批。"
    )

    chunks = split_text(sample_text, chunk_size=80, chunk_overlap=15)
    assert len(chunks) >= 3

    docs = [Document(page_content=sample_text, metadata={"source": "fin_policy.md", "category": "FINANCE"})]
    chunked = split_documents(docs, chunk_size=80, chunk_overlap=15)

    assert len(chunked) >= 3
    assert chunked[0].metadata["chunk_index"] == 0
    assert chunked[0].metadata["total_chunks"] == len(chunked)
    assert chunked[0].metadata["category"] == "FINANCE"
    assert chunked[0].metadata["char_count"] == len(chunked[0].page_content)


def test_qdrant_info_and_memory_isolation():
    """Validates Qdrant telemetry information and memory client isolation."""
    mem_client = get_qdrant_client(memory=True)
    info = get_qdrant_info(mem_client)

    assert info["status"] == "healthy"
    assert "embedding_engine" in info

    docs = [
        Document(page_content="IT运维部打印机驱动下载与配置说明", metadata={"category": "IT"}),
        Document(page_content="泛微OA工单流转异常应急预案", metadata={"category": "IT"}),
    ]
    upserted = upsert_documents(docs, collection_name="test_diag_col", client=mem_client)
    assert upserted == 2

    res = search_similar_documents("打印机驱动安装", top_k=1, collection_name="test_diag_col", client=mem_client)
    assert len(res) == 1
    assert "打印机" in res[0].page_content


def test_ingest_knowledge_base_pipeline(tmp_path: Path):
    """Validates the complete ingest_knowledge_base orchestration function."""
    # Create synthetic sample knowledge folder
    hr_file = tmp_path / "01_HR_TEST.md"
    hr_file.write_text("# 考勤制度\n\n员工迟到15分钟以内免扣除，每月限3次。", encoding="utf-8")

    proc_file = tmp_path / "02_PROCUREMENT_TEST.md"
    proc_file.write_text("# 采购制度\n\n超过10000元的采购需部门经理审批。", encoding="utf-8")

    mem_client = QdrantClient(":memory:")
    report = ingest_knowledge_base(
        kb_dir=tmp_path,
        collection_name="test_ingest_pipeline",
        chunk_size=300,
        chunk_overlap=20,
        recreate=True,
        verify=True,
        client=mem_client,
    )

    assert report["status"] == "success"
    assert report["raw_documents_count"] == 2
    assert report["chunks_indexed"] >= 2
    assert "HR" in report["category_breakdown"]
    assert "PROCUREMENT" in report["category_breakdown"]
    assert len(report["verification_probes"]) > 0


def test_knowledge_status_and_sync_api():
    """Validates GET /api/v1/knowledge/status and POST /api/v1/knowledge/sync endpoints."""
    admin_token = create_access_token(data={"sub": "admin_user", "role": "admin"})
    employee_token = create_access_token(data={"sub": "emp_user", "role": "employee"})

    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    emp_headers = {"Authorization": f"Bearer {employee_token}"}

    # 1. GET /status with employee token
    resp = client.get("/api/v1/knowledge/status", headers=emp_headers)
    assert resp.status_code == 200
    res_data = resp.json()["data"]
    assert res_data["status"] == "healthy"
    assert "points_count" in res_data
    assert "embedding_engine" in res_data
    assert "sample_kb_files" in res_data

    # 2. POST /sync with employee token (Forbidden, requires ADMIN/MANAGER)
    sync_resp_forbidden = client.post("/api/v1/knowledge/sync", headers=emp_headers)
    assert sync_resp_forbidden.status_code in [401, 403]

    # 3. POST /sync with admin token
    sync_resp = client.post("/api/v1/knowledge/sync?recreate=false", headers=admin_headers)
    assert sync_resp.status_code == 200
    sync_data = sync_resp.json()["data"]
    assert sync_data["status"] == "success"
    assert sync_data["chunks_indexed"] >= 1
