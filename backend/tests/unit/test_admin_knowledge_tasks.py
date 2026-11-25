"""Unit Tests for Issue-0058: Admin Knowledge Upload, Inventory, Sync & Async Task Center."""

from pathlib import Path
from typing import Dict
import pytest
from fastapi.testclient import TestClient
from qdrant_client import QdrantClient

import backend.api.v1.knowledge as knowledge_api
import backend.api.v1.tasks as tasks_api
import backend.core.knowledge_ledger as ledger_module
import backend.rag.retriever as retriever_module
import backend.rag.vector_store as vector_store_module
import backend.scripts.ingest_knowledge as ingest_script
from backend.main import app
from backend.tasks.celery_app import celery_app


@pytest.fixture(autouse=True)
def isolated_knowledge_env(tmp_path: Path, monkeypatch):
    """Isolates uploaded DATA_DIR, knowledge_ledger JSON, Qdrant client, and Celery config."""
    temp_data_dir = tmp_path / "uploaded_data"
    temp_data_dir.mkdir(parents=True, exist_ok=True)
    temp_ledger_path = tmp_path / "logs" / "knowledge_tasks_ledger.json"

    monkeypatch.setattr(knowledge_api, "DATA_DIR", temp_data_dir)
    monkeypatch.setattr(ledger_module, "LEDGER_PATH", temp_ledger_path)
    ledger_module.reset_ledger_cache()

    mem_qdrant = QdrantClient(":memory:")
    monkeypatch.setattr(vector_store_module, "get_qdrant_client", lambda *a, **kw: mem_qdrant)
    monkeypatch.setattr(ingest_script, "get_qdrant_client", lambda *a, **kw: mem_qdrant)
    monkeypatch.setattr(retriever_module, "get_qdrant_client", lambda *a, **kw: mem_qdrant)
    monkeypatch.setattr(
        knowledge_api,
        "get_qdrant_info",
        lambda *a, **kw: vector_store_module.get_qdrant_info(client=mem_qdrant),
    )

    # Reset singleton HybridRetriever so each test gets clean in-memory state
    monkeypatch.setattr(retriever_module, "_global_hybrid_retriever", None)

    orig_eager = celery_app.conf.task_always_eager
    orig_propagates = celery_app.conf.task_eager_propagates
    orig_store_eager = celery_app.conf.task_store_eager_result
    orig_backend = celery_app.conf.result_backend

    yield {
        "data_dir": temp_data_dir,
        "ledger_path": temp_ledger_path,
        "qdrant": mem_qdrant,
    }

    ledger_module.reset_ledger_cache()
    celery_app.conf.update(
        task_always_eager=orig_eager,
        task_eager_propagates=orig_propagates,
        task_store_eager_result=orig_store_eager,
        result_backend=orig_backend,
    )


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _auth_header_for(client: TestClient, username: str) -> Dict[str, str]:
    resp = client.post("/api/v1/auth/switch-role", json={"username": username})
    assert resp.status_code == 200
    token = resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_admin_knowledge_and_task_endpoints_rbac(client: TestClient, tmp_path: Path):
    """Enforces 401/403 on admin endpoints while preserving status/search for employee and manager."""
    sample_file = tmp_path / "rbac_probe.md"
    sample_file.write_text("# 权限校验测试文档\n\n仅系统管理员可上传与同步。", encoding="utf-8")

    # 1. Unauthenticated -> 401 across protected endpoints
    assert client.get("/api/v1/knowledge/status").status_code == 401
    assert client.get("/api/v1/knowledge/documents").status_code == 401
    assert client.post("/api/v1/knowledge/sync").status_code == 401
    assert client.get("/api/v1/tasks").status_code == 401
    assert client.get("/api/v1/tasks/demo-task-1/status").status_code == 401
    assert client.get("/api/v1/knowledge/search", params={"query": "年假"}).status_code == 401
    assert client.post("/api/v1/knowledge/search", json={"query": "年假"}).status_code == 401
    with open(sample_file, "rb") as f:
        assert (
            client.post(
                "/api/v1/knowledge/upload",
                files={"file": ("rbac_probe.md", f, "text/markdown")},
            ).status_code
            == 401
        )

    # 2. Employee & Manager -> 403 on admin mutations/tasks, 200 on status/search
    for username in ("employee", "manager"):
        headers = _auth_header_for(client, username)

        assert client.get("/api/v1/knowledge/documents", headers=headers).status_code == 403
        assert client.post("/api/v1/knowledge/sync", headers=headers).status_code == 403
        assert client.get("/api/v1/tasks", headers=headers).status_code == 403
        assert client.get("/api/v1/tasks/demo-task-1/status", headers=headers).status_code == 403
        with open(sample_file, "rb") as f:
            assert (
                client.post(
                    "/api/v1/knowledge/upload",
                    files={"file": ("rbac_probe.md", f, "text/markdown")},
                    headers=headers,
                ).status_code
                == 403
            )

        status_resp = client.get("/api/v1/knowledge/status", headers=headers)
        assert status_resp.status_code == 200
        assert "points_count" in status_resp.json()["data"]

        search_get = client.get(
            "/api/v1/knowledge/search",
            params={"query": "年假", "top_k": 2},
            headers=headers,
        )
        assert search_get.status_code == 200
        assert "results" in search_get.json()["data"]

        search_post = client.post(
            "/api/v1/knowledge/search",
            json={"query": "采购审批", "top_k": 2},
            headers=headers,
        )
        assert search_post.status_code == 200
        assert "results" in search_post.json()["data"]

    # 3. Admin -> 200 on inventory & tasks ledger
    admin_headers = _auth_header_for(client, "admin")
    assert client.get("/api/v1/knowledge/documents", headers=admin_headers).status_code == 200
    assert client.get("/api/v1/tasks", headers=admin_headers).status_code == 200


def test_upload_single_file_validation_and_path_traversal(
    client: TestClient,
    isolated_knowledge_env,
    monkeypatch,
):
    """Rejects unsupported formats, empty payloads, path traversal, and oversized files with HTTP 400."""
    admin_headers = _auth_header_for(client, "admin")
    data_dir: Path = isolated_knowledge_env["data_dir"]

    # 1. Unsupported extension
    bad_ext = client.post(
        "/api/v1/knowledge/upload",
        files={"file": ("payload.exe", b"binary-blob", "application/octet-stream")},
        headers=admin_headers,
    )
    assert bad_ext.status_code == 400

    # 2. Empty file (0 bytes)
    empty_resp = client.post(
        "/api/v1/knowledge/upload",
        files={"file": ("empty_policy.md", b"", "text/markdown")},
        headers=admin_headers,
    )
    assert empty_resp.status_code == 400

    # 3. Path traversal
    traversal_resp = client.post(
        "/api/v1/knowledge/upload",
        files={"file": ("../../escape_policy.md", b"# evil", "text/markdown")},
        headers=admin_headers,
    )
    assert traversal_resp.status_code == 400
    assert not (data_dir / "escape_policy.md").exists()

    # 4. Oversized file limit
    monkeypatch.setattr(knowledge_api, "MAX_UPLOAD_SIZE_BYTES", 64)
    oversize_resp = client.post(
        "/api/v1/knowledge/upload",
        files={"file": ("large_policy.md", b"A" * 128, "text/markdown")},
        headers=admin_headers,
    )
    assert oversize_resp.status_code == 400

    # 5. Corrupt PDF payload fails gracefully and cleans up unindexed artifact
    corrupt_resp = client.post(
        "/api/v1/knowledge/upload",
        files={"file": ("corrupt_policy.pdf", b"not-a-valid-pdf-stream", "application/pdf")},
        headers=admin_headers,
    )
    assert corrupt_resp.status_code == 400
    assert not (data_dir / "corrupt_policy.pdf").exists()


def test_admin_sync_upload_inventory_ledger_and_hybrid_search(
    client: TestClient,
    isolated_knowledge_env,
):
    """Verifies sync upload (.md & .txt), ledger persistence, inventory listing, and HybridRetriever search."""
    admin_headers = _auth_header_for(client, "admin")
    data_dir: Path = isolated_knowledge_env["data_dir"]

    # 1. Upload Markdown document synchronously
    md_content = "# 研发GPU集群配额制度\n\n申请 A100 算力节点超过 8 卡需提交架构委员会与管理员联合审批。".encode(
        "utf-8"
    )
    upload_md = client.post(
        "/api/v1/knowledge/upload",
        files={"file": ("gpu_quota_policy.md", md_content, "text/markdown")},
        data={"category": "IT", "is_async": "false"},
        headers=admin_headers,
    )
    assert upload_md.status_code == 200
    md_data = upload_md.json()["data"]
    assert md_data["filename"] == "gpu_quota_policy.md"
    assert md_data["category"] == "IT"
    assert md_data["is_async"] is False
    assert md_data["execution_mode"] == "sync"
    assert md_data["status"] == "COMPLETED"
    assert md_data["chunks_indexed"] >= 1
    assert md_data["task_id"].startswith("sync-")
    assert (data_dir / "gpu_quota_policy.md").exists()

    # 2. Upload plain-text (.txt) document synchronously
    txt_content = "2026年员工弹性办公补充通知：研发中心核心协作时段为 10:30 至 16:30。".encode("utf-8")
    upload_txt = client.post(
        "/api/v1/knowledge/upload",
        files={"file": ("flexible_work_notice.txt", txt_content, "text/plain")},
        data={"category": "HR", "is_async": "false"},
        headers=admin_headers,
    )
    assert upload_txt.status_code == 200
    txt_data = upload_txt.json()["data"]
    assert txt_data["filename"] == "flexible_work_notice.txt"
    assert txt_data["category"] == "HR"
    assert txt_data["chunks_indexed"] >= 1

    # 3. Task status & 5-stage pipeline steps
    task_status = client.get(f"/api/v1/tasks/{md_data['task_id']}/status", headers=admin_headers)
    assert task_status.status_code == 200
    t_payload = task_status.json()["data"]
    assert t_payload["status"] == "SUCCESS"
    assert t_payload["ready"] is True
    assert t_payload["successful"] is True
    assert t_payload["progress"]["current"] == 100
    assert len(t_payload["steps"]) == 5
    assert all(step["status"] == "success" for step in t_payload["steps"])

    # 4. Tasks overview ledger
    tasks_list = client.get("/api/v1/tasks", headers=admin_headers)
    assert tasks_list.status_code == 200
    overview = tasks_list.json()["data"]
    assert overview["summary"]["completed"] >= 2
    task_ids = {item["task_id"] for item in overview["tasks"]}
    assert md_data["task_id"] in task_ids
    assert txt_data["task_id"] in task_ids

    # 5. Documents inventory includes built-in + uploaded
    inv_resp = client.get("/api/v1/knowledge/documents", headers=admin_headers)
    assert inv_resp.status_code == 200
    inv = inv_resp.json()["data"]
    assert inv["uploaded_count"] == 2
    assert inv["builtin_count"] >= 1
    assert inv["total_count"] == inv["builtin_count"] + inv["uploaded_count"]
    uploaded_names = {d["filename"] for d in inv["documents"] if d["source_type"] == "uploaded"}
    assert uploaded_names == {"gpu_quota_policy.md", "flexible_work_notice.txt"}

    # 6. Immediate HybridRetriever search finds newly uploaded content
    emp_headers = _auth_header_for(client, "employee")
    search_resp = client.post(
        "/api/v1/knowledge/search",
        json={"query": "A100 算力节点 8卡 审批", "top_k": 5, "category_filter": "IT"},
        headers=emp_headers,
    )
    assert search_resp.status_code == 200
    hits = search_resp.json()["data"]["results"]
    assert any(h["metadata"].get("filename") == "gpu_quota_policy.md" for h in hits)


def test_admin_async_upload_offline_fallback_and_apply_async_recovery(
    client: TestClient,
    monkeypatch,
):
    """Ensures is_async=true falls back gracefully when Redis/Celery Worker is offline without 500 or ghost tasks."""
    admin_headers = _auth_header_for(client, "admin")

    # Case A: Redis Broker port closed / unreachable
    celery_app.conf.update(task_always_eager=False)
    monkeypatch.setattr(knowledge_api.settings, "REDIS_HOST", "127.0.0.1")
    monkeypatch.setattr(knowledge_api.settings, "REDIS_PORT", 59999)
    monkeypatch.setattr(celery_app.conf, "broker_url", "redis://127.0.0.1:59999/0")

    resp = client.post(
        "/api/v1/knowledge/upload",
        files={"file": ("async_fallback_proc.md", "# 采购招标补充条款\n超过三万元需三家比价。".encode("utf-8"), "text/markdown")},
        data={"category": "PROCUREMENT", "is_async": "true"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    payload = resp.json()["data"]
    assert payload["is_async"] is True
    assert payload["status"] == "SUBMITTED"
    assert payload["execution_mode"] == "async_fallback"
    assert payload["fallback_reason"]
    assert payload["task_id"].startswith("fb-")

    # BackgroundTasks executes on TestClient response exit -> task status completes cleanly
    status_resp = client.get(f"/api/v1/tasks/{payload['task_id']}/status", headers=admin_headers)
    assert status_resp.status_code == 200
    status_data = status_resp.json()["data"]
    assert status_data["status"] == "SUCCESS"
    assert status_data["stage"] == "COMPLETED"
    assert status_data["ready"] is True
    assert status_data["result"]["chunks_indexed"] >= 1

    # Case B: _can_dispatch_celery returns True, but apply_async raises ConnectionError -> reuses task_id cleanly
    async def _fake_can_dispatch():
        return True, "celery_worker", None

    def _failing_apply_async(*args, **kwargs):
        raise ConnectionError("Simulated Redis connection drop during apply_async")

    monkeypatch.setattr(knowledge_api, "_can_dispatch_celery", _fake_can_dispatch)
    monkeypatch.setattr(knowledge_api.async_ingest_document, "apply_async", _failing_apply_async)

    resp_b = client.post(
        "/api/v1/knowledge/upload",
        files={"file": ("apply_async_recover.txt", "异常切换后台异步队列验证内容".encode("utf-8"), "text/plain")},
        data={"category": "SECURITY", "is_async": "true"},
        headers=admin_headers,
    )
    assert resp_b.status_code == 200
    data_b = resp_b.json()["data"]
    assert data_b["execution_mode"] == "async_fallback"

    tasks_after = client.get("/api/v1/tasks", headers=admin_headers).json()["data"]["tasks"]
    matching = [t for t in tasks_after if t["task_id"] == data_b["task_id"]]
    assert len(matching) == 1
    assert matching[0]["status"] == "SUCCESS"


def test_admin_async_upload_celery_eager_and_offline_status_guard(
    client: TestClient,
    monkeypatch,
):
    """Tests Celery eager async upload pipeline and resilient task status query when AsyncResult fails."""
    admin_headers = _auth_header_for(client, "admin")
    celery_app.conf.update(
        task_always_eager=True,
        task_eager_propagates=True,
        task_store_eager_result=True,
        result_backend="cache+memory://",
    )

    resp = client.post(
        "/api/v1/knowledge/upload",
        files={"file": ("eager_policy.txt", "Celery Eager 模式切片与状态追踪测试".encode("utf-8"), "text/plain")},
        data={"category": "CS", "is_async": "true"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["is_async"] is True
    assert data["execution_mode"] == "celery_eager"
    assert data["fallback_reason"] is None

    status_resp = client.get(f"/api/v1/tasks/{data['task_id']}/status", headers=admin_headers)
    assert status_resp.status_code == 200
    status_data = status_resp.json()["data"]
    assert status_data["status"] == "SUCCESS"
    assert status_data["ready"] is True
    assert status_data["result"]["chunks_indexed"] >= 1
    assert all(s["status"] == "success" for s in status_data["steps"])

    # Simulate AsyncResult raising exception for unknown task_id when Redis backend is down
    class BrokenAsyncResult:
        def __init__(self, *args, **kwargs):
            raise ConnectionError("Redis result backend offline")

    monkeypatch.setattr(tasks_api, "AsyncResult", BrokenAsyncResult)
    offline_status = client.get("/api/v1/tasks/nonexistent-offline-task/status", headers=admin_headers)
    assert offline_status.status_code == 200
    offline_data = offline_status.json()["data"]
    assert offline_data["status"] == "PENDING"
    assert offline_data["stage"] == "QUEUED"
    assert len(offline_data["steps"]) == 5


def test_admin_knowledge_sync_incremental_and_recreate(
    client: TestClient,
    isolated_knowledge_env,
):
    """Verifies POST /api/v1/knowledge/sync?recreate=false|true reindexes sample_kb + uploaded docs and logs tasks."""
    admin_headers = _auth_header_for(client, "admin")

    # Upload a custom file first
    upload_resp = client.post(
        "/api/v1/knowledge/upload",
        files={"file": ("custom_sync_guide.md", "# 同步测试手册\n\n用于验证全库重建同步包含上传文件。".encode("utf-8"), "text/markdown")},
        data={"category": "GENERAL", "is_async": "false"},
        headers=admin_headers,
    )
    assert upload_resp.status_code == 200

    # 1. Incremental sync
    sync_inc = client.post("/api/v1/knowledge/sync?recreate=false", headers=admin_headers)
    assert sync_inc.status_code == 200
    inc_data = sync_inc.json()["data"]
    assert inc_data["status"] == "success"
    assert inc_data["recreate"] is False
    assert inc_data["chunks_indexed"] >= 1
    assert inc_data["uploaded_reindexed_files"] == 1
    assert inc_data["qdrant_info"]["points_count"] >= inc_data["chunks_indexed"]

    # 2. Full recreate sync
    sync_rec = client.post("/api/v1/knowledge/sync?recreate=true", headers=admin_headers)
    assert sync_rec.status_code == 200
    rec_data = sync_rec.json()["data"]
    assert rec_data["status"] == "success"
    assert rec_data["recreate"] is True
    assert rec_data["uploaded_reindexed_files"] == 1
    assert rec_data["qdrant_info"]["points_count"] >= rec_data["chunks_indexed"]

    # Confirm sync task is recorded in /api/v1/tasks
    tasks_overview = client.get("/api/v1/tasks", headers=admin_headers).json()["data"]
    sync_tasks = [t for t in tasks_overview["tasks"] if t["task_type"] == "sync"]
    assert len(sync_tasks) >= 2
    assert sync_tasks[0]["status"] == "SUCCESS"
    assert sync_tasks[0]["execution_mode"] == "sync_rebuild"
