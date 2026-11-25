"""Unit Tests for Issue-0059: Admin System Telemetry, Tool Audit & P0-P4 SLA Monitoring."""

import importlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Generator
import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import HumanMessage
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import backend.api.v1.monitoring as monitoring_api
import backend.core.knowledge_ledger as ledger_module
import backend.core.runtime_config as runtime_config_module
from backend.api.v1.chat_ws import ConnectionManager
from backend.core.config import settings
from backend.core.llm_gateway import LLMGateway as ShadowLLMGateway
from backend.core.llm_infra import LLMGateway as InfraLLMGateway
from backend.core.metrics import (
    active_websocket_connections,
    clear_tool_audits,
    estimate_token_count,
    get_recent_tool_audits,
    record_cache_hit,
    record_cache_miss,
    record_llm_tokens,
    record_tool_execution,
    record_ttft,
    set_active_ws_connections,
)
from backend.db.session import Base, get_db
from backend.main import app
from backend.models.approval import Approval
from backend.models.chat import ChatMessage, ChatSession
from backend.models.ticket import Ticket
from backend.tools.registry import registry

generate_node_module = importlib.import_module("backend.graph.nodes.generate_node")


@pytest.fixture(autouse=True)
def isolated_monitoring_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[Dict[str, Any], None, None]:
    """Isolates database session, runtime config overrides, ledger path, and global settings."""
    db_file = tmp_path / "monitoring_test.db"
    test_engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def _override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    orig_overrides = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = _override_get_db

    temp_cfg_file = tmp_path / "runtime_config.json"
    monkeypatch.setattr(runtime_config_module, "RUNTIME_CONFIG_PATH", temp_cfg_file)
    temp_ledger_path = tmp_path / "logs" / "knowledge_tasks_ledger.json"
    monkeypatch.setattr(ledger_module, "LEDGER_PATH", temp_ledger_path)
    ledger_module.reset_ledger_cache()

    orig_api_key = settings.LLM_API_KEY
    orig_secret_key = settings.SECRET_KEY
    orig_ws_val = int(active_websocket_connections._value.get())

    runtime_config_module.reset_runtime_config(updated_by="monitoring_test_setup")

    yield {
        "session_factory": TestingSessionLocal,
        "ledger_path": temp_ledger_path,
    }

    app.dependency_overrides = orig_overrides
    settings.LLM_API_KEY = orig_api_key
    settings.SECRET_KEY = orig_secret_key
    set_active_ws_connections(orig_ws_val)
    runtime_config_module.reset_runtime_config(updated_by="monitoring_test_teardown")
    ledger_module.reset_ledger_cache()
    test_engine.dispose()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _auth_header_for(client: TestClient, username: str) -> Dict[str, str]:
    resp = client.post("/api/v1/auth/switch-role", json={"username": username})
    assert resp.status_code == 200
    token = resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_monitoring_overview_rbac_and_zero_secret_leakage(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Enforces 401/403/200 RBAC isolation and prevents plaintext API/JWT secret exposure."""
    settings.LLM_API_KEY = "sk-monitoring-super-secret-value-9988"
    test_jwt_secret = settings.SECRET_KEY

    async def _redis_down() -> bool:
        return False

    monkeypatch.setattr(monitoring_api, "check_redis_health", _redis_down)

    # 1. Unauthenticated -> 401
    unauth_resp = client.get("/api/v1/admin/monitoring/overview")
    assert unauth_resp.status_code == 401

    # 2. Employee & Manager -> 403 Forbidden
    for username in ("employee", "manager"):
        headers = _auth_header_for(client, username)
        forbidden_resp = client.get("/api/v1/admin/monitoring/overview", headers=headers)
        assert forbidden_resp.status_code == 403

    # 3. Admin -> 200 OK with masked key and zero plaintext secret
    admin_headers = _auth_header_for(client, "admin")
    ok_resp = client.get("/api/v1/admin/monitoring/overview", headers=admin_headers)
    assert ok_resp.status_code == 200
    body = ok_resp.json()
    assert body["code"] == 200

    data = body["data"]
    assert data["operator"]["role"] == "admin"
    assert data["system_health"]["overall_status"] == "DEGRADED"
    assert data["system_health"]["llm_engine"]["has_api_key"] is True
    assert data["system_health"]["llm_engine"]["api_key_masked"] == "sk-****9988"

    raw_payload = ok_resp.text
    assert "sk-monitoring-super-secret-value-9988" not in raw_payload
    assert test_jwt_secret not in raw_payload

    # 4. Health status flips to HEALTHY when all components are UP
    async def _redis_up() -> bool:
        return True

    monkeypatch.setattr(monitoring_api, "check_redis_health", _redis_up)
    monkeypatch.setattr(monitoring_api, "check_mysql_health", lambda: True)
    monkeypatch.setattr(monitoring_api, "check_qdrant_health", lambda: True)
    healthy_resp = client.get("/api/v1/admin/monitoring/overview", headers=admin_headers)
    assert healthy_resp.status_code == 200
    assert healthy_resp.json()["data"]["system_health"]["overall_status"] == "HEALTHY"


@pytest.mark.asyncio
async def test_prometheus_ttft_buckets_tokens_cache_and_ws_gauge(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies non-cumulative TTFT 5-bucket deltas, token counters, LLMGateway cache hits, and WS gauge."""

    async def _redis_down() -> bool:
        return False

    monkeypatch.setattr(monitoring_api, "check_redis_health", _redis_down)
    admin_headers = _auth_header_for(client, "admin")

    baseline = client.get("/api/v1/admin/monitoring/overview", headers=admin_headers).json()["data"]["telemetry"]
    base_ttft_total = baseline["ttft"]["total_observations"]
    base_buckets = {b["bucket"]: b["count"] for b in baseline["ttft"]["buckets"]}
    base_in_tokens = baseline["tokens"]["input_tokens"]
    base_out_tokens = baseline["tokens"]["output_tokens"]
    base_hits = baseline["prompt_cache"]["hits"]
    base_misses = baseline["prompt_cache"]["misses"]

    # 1. Emit exactly one observation into each of the 5 discrete TTFT ranges
    for sample_sec in (0.04, 0.18, 0.35, 0.90, 2.20):
        record_ttft(sample_sec)

    # 2. Emit direct LLM tokens + run ShadowLLMGateway cache miss -> hit + InfraLLMGateway token/cache tracking
    record_llm_tokens("qwen3.5:2b", "input", 240)
    record_llm_tokens("qwen3.5:2b", "output", 110)

    gateway = ShadowLLMGateway(primary_model="gateway-test-model", enable_cache=True)

    async def _dummy_caller(model: str, prompt: str, system_prompt: str | None = None) -> str:
        return f"OK from {model}: {prompt}"

    miss_res = await gateway.invoke(prompt="差旅报销标准是什么", llm_caller=_dummy_caller)
    hit_res = await gateway.invoke(prompt="差旅报销标准是什么", llm_caller=_dummy_caller)
    assert miss_res.cached is False
    assert hit_res.cached is True

    infra_gw = InfraLLMGateway(primary_model_name="infra-primary-v1", fallback_model_name="infra-backup-v1")

    async def _no_redis() -> None:
        return None

    monkeypatch.setattr(infra_gw, "_get_redis", _no_redis)

    async def _infra_primary(prompt: str) -> str:
        return f"Infra reply for {prompt}"

    infra_res = await infra_gw.generate_response("报销审批需要哪些材料", primary_func=_infra_primary, use_cache=False)
    assert infra_res["model_used"] == "infra-primary-v1"

    # 3. Also verify generate_node token telemetry emission under offline fallback
    runtime_config_module.update_runtime_config(
        {"llm_provider": "local_fallback", "llm_model": "local-enterprise-agent-v1"},
        updated_by="monitoring_test",
    )
    await generate_node_module.generate_node(
        {
            "messages": [HumanMessage(content="测试监控 Token 上报")],
            "intent": "chat",
            "context": [],
            "metadata": {},
        }
    )

    # 4. Exercise WebSocket ConnectionManager gauge tracking
    class _FakeWS:
        async def accept(self) -> None:
            return None

    ws_mgr = ConnectionManager()
    ws_one = _FakeWS()
    ws_two = _FakeWS()
    await ws_mgr.connect("c1", ws_one)  # type: ignore[arg-type]
    await ws_mgr.connect("c2", ws_two)  # type: ignore[arg-type]
    assert int(active_websocket_connections._value.get()) == 2
    ws_mgr.disconnect("c1", ws_one)  # type: ignore[arg-type]

    after = client.get("/api/v1/admin/monitoring/overview", headers=admin_headers).json()["data"]["telemetry"]

    # Non-cumulative TTFT bucket check: each bucket must increment by exact 1
    assert after["ttft"]["total_observations"] == base_ttft_total + 5
    after_buckets = {b["bucket"]: b["count"] for b in after["ttft"]["buckets"]}
    for label in ("<= 100ms", "100ms - 250ms", "250ms - 500ms", "500ms - 1.5s", "> 1.5s"):
        assert after_buckets[label] == base_buckets[label] + 1

    # Token & cache check
    assert after["tokens"]["input_tokens"] > base_in_tokens + 240
    assert after["tokens"]["output_tokens"] > base_out_tokens + 110
    assert after["tokens"]["total_tokens"] == after["tokens"]["input_tokens"] + after["tokens"]["output_tokens"]
    assert any(m["model"] == "qwen3.5:2b" for m in after["tokens"]["by_model"])

    assert after["prompt_cache"]["misses"] == base_misses + 1
    assert after["prompt_cache"]["hits"] == base_hits + 1
    assert after["active_websocket_connections"] == 1

    # Explicit cache helpers sanity
    record_cache_hit(2)
    record_cache_miss(1)
    assert estimate_token_count("测试中文 token 估算") >= 4


@pytest.mark.asyncio
async def test_tool_registry_telemetry_and_sanitized_audit_buffer(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies ToolRegistry telemetry instrumentation, error handling, and secret redaction in audit buffer."""

    async def _redis_down() -> bool:
        return False

    monkeypatch.setattr(monitoring_api, "check_redis_health", _redis_down)
    clear_tool_audits()

    def _probe_ok_tool(query: str) -> Dict[str, Any]:
        return {"status": "SUCCESS", "ticket_id": "TICK-PROBE-01", "echo": query}

    def _probe_fail_tool(fail_reason: str) -> Dict[str, Any]:
        raise RuntimeError(f"upstream failed with sk-secrettooltoken123456: {fail_reason}")

    orig_tools = dict(registry._tools)
    try:
        registry.register(_probe_ok_tool, name="probe_ok_tool", description="监控测试正常工具")
        registry.register(_probe_fail_tool, name="probe_fail_tool", description="监控测试异常工具")

        ok_res = await registry.execute_tool("probe_ok_tool", {"query": "ping"})
        assert ok_res["ticket_id"] == "TICK-PROBE-01"

        with pytest.raises(RuntimeError):
            await registry.execute_tool("probe_fail_tool", {"fail_reason": "timeout"})

        record_tool_execution(
            tool_name="probe_ok_tool",
            status="success",
            duration_seconds=0.015,
            summary="Bearer eyJhbGciOiJIUzI1NiJ9.abcdef1234567890",
        )

        admin_headers = _auth_header_for(client, "admin")
        resp = client.get("/api/v1/admin/monitoring/overview?audit_limit=2", headers=admin_headers)
        assert resp.status_code == 200
        tools_data = resp.json()["data"]["telemetry"]["tools"]

        assert tools_data["registered_count"] >= 6
        assert tools_data["success_calls"] >= 2
        assert tools_data["error_calls"] >= 1

        by_name = {item["tool_name"]: item for item in tools_data["by_tool"]}
        assert by_name["probe_ok_tool"]["success_count"] >= 2
        assert by_name["probe_fail_tool"]["error_count"] >= 1

        audits = tools_data["recent_audits"]
        assert len(audits) == 2
        assert audits[0]["tool_name"] == "probe_ok_tool"
        assert "[REDACTED]" in audits[0]["summary"]
        assert "eyJhbGciOiJIUzI1NiJ9" not in audits[0]["summary"]

        all_audits = get_recent_tool_audits(limit=10)
        assert any(a["tool_name"] == "probe_fail_tool" and "sk-secrettooltoken" not in a["summary"] for a in all_audits)
    finally:
        registry._tools = orig_tools
        clear_tool_audits()


def test_orm_chat_approvals_p0_p4_sla_and_ingestion_tasks_aggregation(
    client: TestClient,
    isolated_monitoring_env: Dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies ORM aggregation for ChatSession/Message, Approvals, P0-P4 SLA compliance, and active tasks."""

    async def _redis_down() -> bool:
        return False

    monkeypatch.setattr(monitoring_api, "check_redis_health", _redis_down)

    session_factory = isolated_monitoring_env["session_factory"]
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)

    with session_factory() as db:
        # 2 active sessions + 1 soft-deleted
        db.add_all(
            [
                ChatSession(session_id="s-mon-1", user_id="employee", title="差旅报销咨询", is_deleted=False),
                ChatSession(session_id="s-mon-2", user_id="manager", title="采购申请", is_deleted=False),
                ChatSession(session_id="s-mon-del", user_id="employee", title="已删除会话", is_deleted=True),
            ]
        )
        # 2 user + 2 assistant messages (avg duration = (2.0 + 4.0) / 2 = 3.0s)
        db.add_all(
            [
                ChatMessage(session_id="s-mon-1", role="user", content="Q1"),
                ChatMessage(session_id="s-mon-1", role="assistant", content="A1", duration_seconds=2.0),
                ChatMessage(session_id="s-mon-2", role="user", content="Q2"),
                ChatMessage(session_id="s-mon-2", role="assistant", content="A2", duration_seconds=4.0),
            ]
        )
        # 4 Approvals: 1 PENDING, 2 APPROVED, 1 REJECTED -> closure = 75.0%
        db.add_all(
            [
                Approval(
                    approval_id="APR-MON-1",
                    thread_id="t1",
                    item_name="A100 GPU",
                    quantity=1,
                    unit_price=50000.0,
                    total_price=50000.0,
                    department="研发部",
                    status="PENDING",
                ),
                Approval(
                    approval_id="APR-MON-2",
                    thread_id="t2",
                    item_name="MacBook Pro",
                    quantity=2,
                    unit_price=15000.0,
                    total_price=30000.0,
                    department="产品部",
                    status="APPROVED",
                ),
                Approval(
                    approval_id="APR-MON-3",
                    thread_id="t3",
                    item_name="显示器",
                    quantity=5,
                    unit_price=3000.0,
                    total_price=15000.0,
                    department="设计部",
                    status="APPROVED",
                ),
                Approval(
                    approval_id="APR-MON-4",
                    thread_id="t4",
                    item_name="非标采购",
                    quantity=1,
                    unit_price=99000.0,
                    total_price=99000.0,
                    department="行政部",
                    status="REJECTED",
                ),
            ]
        )
        # 5 Tickets spanning P0-P3 (leaving P4 empty to test has_tickets=False)
        db.add_all(
            [
                Ticket(
                    ticket_id="TICK-P0-OK",
                    title="核心网关抖动",
                    description="监控告警",
                    priority="P0",
                    department="IT",
                    status="OPEN",
                    created_at=now_utc - timedelta(minutes=5),
                ),
                Ticket(
                    ticket_id="TICK-P0-BREACH",
                    title="主库连接池耗尽",
                    description="超过30分钟未闭环",
                    priority="P0",
                    department="IT",
                    status="OPEN",
                    created_at=now_utc - timedelta(minutes=45),
                ),
                Ticket(
                    ticket_id="TICK-P1-CLOSED",
                    title="VPN 网关证书更新",
                    description="已处理闭环",
                    priority="P1",
                    department="IT",
                    status="RESOLVED",
                    created_at=now_utc - timedelta(minutes=300),
                ),
                Ticket(
                    ticket_id="TICK-P2-BREACH",
                    title="测试环境镜像同步慢",
                    description="超过8小时未闭环",
                    priority="P2",
                    department="IT",
                    status="OPEN",
                    created_at=now_utc - timedelta(minutes=600),
                ),
                Ticket(
                    ticket_id="TICK-P3-OK",
                    title="新员工入职邮箱开通",
                    description="处理中",
                    priority="P3",
                    department="HR",
                    status="OPEN",
                    created_at=now_utc - timedelta(minutes=100),
                ),
            ]
        )
        db.commit()

    # Seed 1 active ingestion task + 1 completed task in isolated ledger
    ledger_module.record_task_created(
        task_id="task-active-1",
        task_type="upload",
        filename="policy_2026.md",
        category="HR",
        execution_mode="async_fallback",
        uploader="admin",
        size_bytes=1024,
        status="PROGRESS",
        stage="INDEXING",
    )
    ledger_module.record_task_created(
        task_id="task-done-2",
        task_type="upload",
        filename="travel.md",
        category="FINANCE",
        execution_mode="sync",
        uploader="admin",
        size_bytes=512,
        status="SUCCESS",
        stage="COMPLETED",
    )

    admin_headers = _auth_header_for(client, "admin")
    resp = client.get("/api/v1/admin/monitoring/overview?ticket_limit=3", headers=admin_headers)
    assert resp.status_code == 200
    payload = resp.json()["data"]

    assert payload["system_health"]["active_ingestion_tasks"] == 1

    chat = payload["business"]["chat"]
    assert chat["active_sessions"] == 2
    assert chat["total_sessions"] == 3
    assert chat["total_messages"] == 4
    assert chat["user_messages"] == 2
    assert chat["assistant_messages"] == 2
    assert chat["avg_thinking_seconds"] == 3.0

    approvals = payload["business"]["approvals"]
    assert approvals["pending_count"] == 1
    assert approvals["approved_count"] == 2
    assert approvals["rejected_count"] == 1
    assert approvals["closed_count"] == 3
    assert approvals["total_count"] == 4
    assert approvals["closure_rate_percent"] == 75.0

    sla = payload["business"]["sla"]
    assert sla["total_tickets"] == 5
    assert sla["open_tickets"] == 4
    assert sla["closed_tickets"] == 1
    assert sla["breached_tickets"] == 2
    assert sla["overall_compliance_percent"] == 60.0
    assert len(sla["recent_tickets"]) == 3

    tiers = {t["priority"]: t for t in sla["tiers"]}
    assert tiers["P0"]["total_count"] == 2
    assert tiers["P0"]["breached_count"] == 1
    assert tiers["P0"]["compliance_rate_percent"] == 50.0
    assert tiers["P1"]["closed_count"] == 1
    assert tiers["P1"]["compliance_rate_percent"] == 100.0
    assert tiers["P2"]["breached_count"] == 1
    assert tiers["P2"]["compliance_rate_percent"] == 0.0
    assert tiers["P3"]["open_count"] == 1
    assert tiers["P3"]["compliance_rate_percent"] == 100.0
    assert tiers["P4"]["has_tickets"] is False
    assert tiers["P4"]["total_count"] == 0
    assert tiers["P4"]["compliance_rate_percent"] == 100.0
