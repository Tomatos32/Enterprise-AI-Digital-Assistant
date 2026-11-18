"""Unit Tests for Issue-0056: JWT Auth, Role Switching, Chat & Approval RBAC Isolation."""

from datetime import datetime
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import backend.api.v1.auth as auth_api_module
import backend.api.v1.approval as approval_api_module
import backend.api.v1.chat_ws as chat_ws_module
import backend.api.v1.workflow as workflow_api_module
from backend.db.session import Base, get_db
from backend.main import app
from backend.models.approval import Approval
from backend.models.chat import ChatMessage, ChatSession


TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    """Yields isolated in-memory SQLite session for tests."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def isolated_db_and_overrides(monkeypatch):
    """Creates clean SQLite tables and cleanly restores dependency overrides after each test."""
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(chat_ws_module, "SessionLocal", TestingSessionLocal)
    workflow_api_module.MOCK_WECOM_MESSAGES.clear()
    yield
    Base.metadata.drop_all(bind=test_engine)
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


def _auth_header_for(client: TestClient, role_or_username: str) -> dict:
    resp = client.post("/api/v1/auth/switch-role", json={"username": role_or_username})
    assert resp.status_code == 200
    token = resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}", "_token": token}


def test_login_and_identities_metadata_have_no_secrets(client):
    """Tests standardized login fields and non-sensitive demo identity listing."""
    login_resp = client.post("/api/v1/auth/login", json={"username": "manager", "password": "manager123"})
    assert login_resp.status_code == 200
    login_data = login_resp.json()["data"]
    assert login_data["username"] == "manager"
    assert login_data["display_name"] == "陈志远"
    assert login_data["role"] == "manager"
    assert login_data["role_label"] == "部门主管"
    assert login_data["department"] == "采购管理部"
    assert "access_token" in login_data

    identities_resp = client.get("/api/v1/auth/identities")
    assert identities_resp.status_code == 200
    identities = identities_resp.json()["data"]
    assert len(identities) == 3
    roles = {item["role"] for item in identities}
    assert roles == {"employee", "manager", "admin"}
    for item in identities:
        assert "password" not in item
        assert "hashed_password" not in item
        assert item["display_name"]
        assert item["department"]
        assert item["role_label"]


def test_switch_role_blocked_in_production_without_mock(client, monkeypatch):
    """Tests demo role switching is blocked in production mode when mock systems are disabled."""
    monkeypatch.setattr(auth_api_module.settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(auth_api_module.settings, "USE_MOCK_SYSTEMS", False)

    resp_list = client.get("/api/v1/auth/identities")
    assert resp_list.status_code == 403

    resp_switch = client.post("/api/v1/auth/switch-role", json={"role": "admin"})
    assert resp_switch.status_code == 403


def test_chat_session_isolation_by_bearer_token(client):
    """Tests per-user session ownership enforcement when Bearer token is provided."""
    emp_auth = _auth_header_for(client, "employee")
    mgr_auth = _auth_header_for(client, "manager")
    emp_headers = {"Authorization": emp_auth["Authorization"]}
    mgr_headers = {"Authorization": mgr_auth["Authorization"]}

    # Employee creates a session (even if passing spoofed user_id, token identity wins)
    create_resp = client.post(
        "/api/v1/chat/sessions",
        json={"title": "员工个人制度咨询", "user_id": "manager"},
        headers=emp_headers,
    )
    assert create_resp.status_code == 200
    emp_session = create_resp.json()
    assert emp_session["user_id"] == "employee"
    emp_sid = emp_session["session_id"]

    # Manager creates a session
    mgr_create = client.post(
        "/api/v1/chat/sessions",
        json={"title": "主管预算复核", "user_id": "manager"},
        headers=mgr_headers,
    )
    assert mgr_create.status_code == 200
    mgr_sid = mgr_create.json()["session_id"]

    # Listing sessions isolates strictly by authenticated user even with spoofed query param
    emp_list = client.get("/api/v1/chat/sessions?user_id=manager", headers=emp_headers)
    assert emp_list.status_code == 200
    emp_ids = {s["session_id"] for s in emp_list.json()}
    assert emp_sid in emp_ids
    assert mgr_sid not in emp_ids

    # Cross-user access / rename / delete / abort -> 403 PermissionDenied
    assert client.get(f"/api/v1/chat/sessions/{mgr_sid}/messages", headers=emp_headers).status_code == 403
    assert client.put(
        f"/api/v1/chat/sessions/{mgr_sid}/title",
        json={"title": "越权篡改"},
        headers=emp_headers,
    ).status_code == 403
    assert client.delete(f"/api/v1/chat/sessions/{mgr_sid}", headers=emp_headers).status_code == 403
    assert client.post("/api/v1/chat/abort", json={"thread_id": mgr_sid}, headers=emp_headers).status_code == 403

    # Owner can still read and rename their own session
    assert client.get(f"/api/v1/chat/sessions/{emp_sid}/messages", headers=emp_headers).status_code == 200


def test_websocket_token_validation_and_cross_user_isolation(client):
    """Tests WebSocket ?token= validation and cross-user session write blocking."""
    with client.websocket_connect("/api/v1/ws/chat/ws_bad_tok?token=invalid.jwt.token") as ws:
        err_frame = ws.receive_json()
        assert err_frame["type"] == "error"
        assert err_frame["status"] == 401

    # Seed a manager-owned session
    db = TestingSessionLocal()
    try:
        db.add(ChatSession(session_id="sess_mgr_private", user_id="manager", title="主管私有会话"))
        db.add(ChatMessage(session_id="sess_mgr_private", role="user", content="预算讨论"))
        db.commit()
    finally:
        db.close()

    emp_auth = _auth_header_for(client, "employee")
    emp_token = emp_auth["_token"]

    with client.websocket_connect(f"/api/v1/ws/chat/ws_emp?token={emp_token}") as ws:
        ws.send_json({
            "message": "尝试写入主管私有会话",
            "thread_id": "thread_iso_001",
            "session_id": "sess_mgr_private",
            "user_id": "manager",
        })
        frame = ws.receive_json()
        assert frame["type"] == "error"
        assert frame["status"] == 403


def test_approval_rbac_and_dynamic_approver_attribution(client, monkeypatch):
    """Tests employee blocking on approval APIs and dynamic approver signature for manager."""
    # Seed a pending approval
    db = TestingSessionLocal()
    try:
        db.add(
            Approval(
                approval_id="APP-TEST-5601",
                thread_id="thread_app_5601",
                item_name="高性能工作站",
                quantity=1,
                unit_price=18000.0,
                total_price=18000.0,
                department="人力资源部",
                reason="业务数据分析",
                status="PENDING",
                created_at=datetime.utcnow(),
            )
        )
        db.commit()
    finally:
        db.close()

    async def fake_graph_ainvoke(*args, **kwargs):
        return {"status": "Resumed"}

    monkeypatch.setattr(approval_api_module.graph, "ainvoke", fake_graph_ainvoke)

    emp_headers = {"Authorization": _auth_header_for(client, "employee")["Authorization"]}
    mgr_headers = {"Authorization": _auth_header_for(client, "manager")["Authorization"]}

    # Employee is blocked from viewing pending approvals, listing all, or acting
    assert client.get("/api/v1/approval/pending", headers=emp_headers).status_code == 403
    assert client.get("/api/v1/approval/list", headers=emp_headers).status_code == 403
    assert client.post(
        "/api/v1/approval/action",
        json={"approval_id": "APP-TEST-5601", "action": "approve", "comment": "越权审批"},
        headers=emp_headers,
    ).status_code == 403

    # Manager can view list & approve with dynamic attribution
    list_resp = client.get("/api/v1/approval/list", headers=mgr_headers)
    assert list_resp.status_code == 200
    assert list_resp.json()["count"] == 1

    act_resp = client.post(
        "/api/v1/approval/action",
        json={"approval_id": "APP-TEST-5601", "action": "approve", "comment": "同意采购"},
        headers=mgr_headers,
    )
    assert act_resp.status_code == 200
    body = act_resp.json()
    assert body["status"] == "SUCCESS"
    assert body["db_status"] == "APPROVED"
    assert "陈志远" in body["approver"]
    assert "采购管理部" in body["approver"]

    assert len(workflow_api_module.MOCK_WECOM_MESSAGES) == 1
    wecom_content = workflow_api_module.MOCK_WECOM_MESSAGES[0]["card"]["markdown"]["content"]
    assert "陈志远" in wecom_content
    assert "系统主管" not in wecom_content

    # Admin can inspect approval queue and admin-only route; manager cannot access admin-only route
    adm_headers = {"Authorization": _auth_header_for(client, "admin")["Authorization"]}
    assert client.get("/api/v1/approval/pending", headers=adm_headers).status_code == 200
    assert client.get("/api/v1/auth/admin-only", headers=adm_headers).status_code == 200
    assert client.get("/api/v1/auth/admin-only", headers=mgr_headers).status_code == 403


def test_headless_backward_compatibility_without_bearer_token(client):
    """Preserves unauthenticated headless compatibility for legacy tests and scripts."""
    create_resp = client.post("/api/v1/chat/sessions", json={"title": "无头兼容会话", "user_id": "u_legacy"})
    assert create_resp.status_code == 200
    assert create_resp.json()["user_id"] == "u_legacy"

    list_resp = client.get("/api/v1/chat/sessions?user_id=u_legacy")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    pending_resp = client.get("/api/v1/approval/pending")
    assert pending_resp.status_code == 200
    assert pending_resp.json()["status"] == "SUCCESS"

