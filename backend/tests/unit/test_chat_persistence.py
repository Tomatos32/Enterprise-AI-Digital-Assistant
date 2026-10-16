"""Unit tests for Chat Session and Message Persistence, REST API & WebSocket Pipeline."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.db.session import Base, get_db
import backend.api.v1.chat_ws as chat_ws_module
from backend.api.v1.chat_ws import (
    _ensure_session_and_record_user_message,
    _record_assistant_message,
)
from backend.models.chat import ChatMessage, ChatSession

# Setup In-Memory SQLite Test Engine
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    """Dependency override for test DB session."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    """Create all tables in memory before each test and drop after."""
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(chat_ws_module, "SessionLocal", TestingSessionLocal)
    yield
    Base.metadata.drop_all(bind=test_engine)
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


def test_chat_session_and_message_orm():
    """Test ChatSession and ChatMessage ORM model creation and querying."""
    db = TestingSessionLocal()
    try:
        session = ChatSession(
            session_id="sess_test_001",
            user_id="u_emp_001",
            title="年假与差旅政策咨询",
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        assert session.id is not None
        assert session.session_id == "sess_test_001"
        assert session.is_deleted is False

        msg1 = ChatMessage(
            session_id="sess_test_001",
            role="user",
            content="请问年假一年有几天？",
        )
        msg2 = ChatMessage(
            session_id="sess_test_001",
            role="assistant",
            content="根据公司规章，工作满1年享有5天带薪年假。",
            sources='["考勤休假管理办法.md"]',
        )
        db.add_all([msg1, msg2])
        db.commit()

        messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == "sess_test_001")
            .order_by(ChatMessage.created_at.asc())
            .all()
        )
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"
        assert "考勤休假管理办法" in messages[1].sources
    finally:
        db.close()


def test_create_session_api(client):
    """Test POST /api/v1/chat/sessions endpoint."""
    payload = {"title": "采购审批新咨询", "user_id": "u_test_user"}
    resp = client.post("/api/v1/chat/sessions", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "采购审批新咨询"
    assert data["user_id"] == "u_test_user"
    assert data["session_id"].startswith("sess_")
    assert data["is_deleted"] is False


def test_list_and_manage_sessions_api(client):
    """Test listing, updating title and deleting chat sessions."""
    # 1. Create 2 sessions
    client.post("/api/v1/chat/sessions", json={"title": "会话A", "user_id": "u_test_list"})
    r2 = client.post("/api/v1/chat/sessions", json={"title": "会话B", "user_id": "u_test_list"})
    sess_b_id = r2.json()["session_id"]

    # 2. List sessions
    list_resp = client.get("/api/v1/chat/sessions?user_id=u_test_list")
    assert list_resp.status_code == 200
    sessions = list_resp.json()
    assert len(sessions) == 2

    # 3. Update title of Session B
    upd_resp = client.put(f"/api/v1/chat/sessions/{sess_b_id}/title", json={"title": "重命名后的会话B"})
    assert upd_resp.status_code == 200
    assert upd_resp.json()["title"] == "重命名后的会话B"

    # 4. Soft delete Session B
    del_resp = client.delete(f"/api/v1/chat/sessions/{sess_b_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "SUCCESS"

    # 5. List again - only Session A remains
    list_resp_after = client.get("/api/v1/chat/sessions?user_id=u_test_list")
    assert len(list_resp_after.json()) == 1
    assert list_resp_after.json()[0]["title"] == "会话A"


def test_session_messages_api(client):
    """Test GET /api/v1/chat/sessions/{session_id}/messages endpoint."""
    r = client.post("/api/v1/chat/sessions", json={"title": "消息历史测试", "user_id": "u_msg_test"})
    sess_id = r.json()["session_id"]

    # Insert messages via direct DB
    db = TestingSessionLocal()
    try:
        db.add(ChatMessage(session_id=sess_id, role="user", content="问题1"))
        db.add(ChatMessage(session_id=sess_id, role="assistant", content="回答1"))
        db.commit()
    finally:
        db.close()

    # Query messages
    resp = client.get(f"/api/v1/chat/sessions/{sess_id}/messages")
    assert resp.status_code == 200
    msgs = resp.json()
    assert len(msgs) == 2
    assert msgs[0]["content"] == "问题1"
    assert msgs[1]["content"] == "回答1"

    # 404 for non-existent session
    resp_404 = client.get("/api/v1/chat/sessions/non_existent_sess/messages")
    assert resp_404.status_code == 404


def test_websocket_persistence_helper_multi_turn():
    """Test multi-turn dialog context loading and message recording helpers."""
    sess_id = "sess_ws_turn_001"
    user_id = "u_ws_tester"

    # Turn 1: User asks first question
    msgs_round1 = _ensure_session_and_record_user_message(
        session_id=sess_id,
        user_id=user_id,
        user_message="我想了解采购电脑的预算上限",
    )
    assert len(msgs_round1) == 1
    assert msgs_round1[0].content == "我想了解采购电脑的预算上限"

    # Turn 1: Assistant replies
    _record_assistant_message(
        session_id=sess_id,
        assistant_message="标准办公笔记本限额为 8000 元，大额采购需主管审批。",
        sources='["采购审批管理制度.md"]',
    )

    # Turn 2: User follows up
    msgs_round2 = _ensure_session_and_record_user_message(
        session_id=sess_id,
        user_id=user_id,
        user_message="如果是程序员申请的高配呢？",
    )
    # msgs_round2 should contain: [HumanMessage(Turn1), AIMessage(Turn1), HumanMessage(Turn2)]
    assert len(msgs_round2) == 3
    assert msgs_round2[0].content == "我想了解采购电脑的预算上限"
    assert "限额为 8000 元" in msgs_round2[1].content
    assert msgs_round2[2].content == "如果是程序员申请的高配呢？"

    # Check DB session title was auto-generated from first question
    db = TestingSessionLocal()
    try:
        session = db.query(ChatSession).filter(ChatSession.session_id == sess_id).first()
        assert session is not None
        assert "采购电脑" in session.title
        assert session.is_deleted is False
    finally:
        db.close()
