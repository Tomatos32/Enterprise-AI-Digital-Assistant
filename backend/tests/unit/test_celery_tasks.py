"""Unit Tests for Celery Asynchronous Task Queue & Task Status Endpoints."""

from pathlib import Path
from fastapi.testclient import TestClient

from backend.main import app
from backend.tasks.celery_app import celery_app
from backend.tasks.ingestion_tasks import async_ingest_document
from backend.core.security import create_access_token

# Configure Celery Task Eager mode, eager result storing, and in-memory cache backend for testing
celery_app.conf.update(
    task_always_eager=True,
    task_eager_propagates=True,
    task_store_eager_result=True,
    result_backend="cache+memory://",
)

client = TestClient(app)


def get_auth_headers():
    """Generates valid JWT Authorization headers for unit tests."""
    token = create_access_token({"sub": "admin", "role": "admin"})
    return {"Authorization": f"Bearer {token}"}


def test_async_ingest_document_task_direct_execution(tmp_path: Path):
    """Tests direct execution of async_ingest_document Celery task in eager mode."""
    test_file = tmp_path / "test_async_sop.md"
    test_file.write_text("# 异步离线处理SOP规章\n本文档用于测试Celery异步解析与向量抽取。", encoding="utf-8")

    # Run task synchronously via .delay()
    task = async_ingest_document.delay(str(test_file), category="PROCUREMENT")
    
    assert task is not None
    assert task.status == "SUCCESS"
    result = task.result
    assert result["filename"] == "test_async_sop.md"
    assert result["chunks_indexed"] >= 1
    assert result["status"] == "COMPLETED"


def test_knowledge_upload_async_endpoint(tmp_path: Path):
    """Tests POST /api/v1/knowledge/upload with is_async=true submitting Celery task."""
    test_file = tmp_path / "async_upload_doc.txt"
    test_file.write_text("异步大文件投递测试内容", encoding="utf-8")

    headers = get_auth_headers()
    with open(test_file, "rb") as f:
        resp = client.post(
            "/api/v1/knowledge/upload",
            files={"file": ("async_upload_doc.txt", f, "text/plain")},
            data={"category": "HR", "is_async": "true"},
            headers=headers
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 200
    assert data["data"]["is_async"] is True
    assert data["data"]["status"] == "SUBMITTED"
    assert "task_id" in data["data"]
    assert len(data["data"]["task_id"]) > 0


def test_get_task_status_endpoint(tmp_path: Path):
    """Tests GET /api/v1/tasks/{task_id}/status returning task progress & details."""
    test_file = tmp_path / "task_status_doc.md"
    test_file.write_text("# 任务状态查询文档\n测试AsyncResult结果透传。", encoding="utf-8")

    task = async_ingest_document.delay(str(test_file), category="IT")
    task_id = task.id

    headers = get_auth_headers()
    resp = client.get(f"/api/v1/tasks/{task_id}/status", headers=headers)
    assert resp.status_code == 200
    res_json = resp.json()
    assert res_json["code"] == 200
    task_data = res_json["data"]
    assert task_data["task_id"] == task_id
    assert task_data["status"] == "SUCCESS"
    assert task_data["ready"] is True
    assert task_data["result"]["chunks_indexed"] >= 1
