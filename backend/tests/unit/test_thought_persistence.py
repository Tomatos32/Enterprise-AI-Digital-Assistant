"""Unit Tests for Deep Thinking CoT & ThoughtLine Database Persistence."""

from pathlib import Path
import sys
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import backend.db.session as db_session
from backend.db.session import Base, SessionLocal, get_db
from backend.main import app
from backend.models.chat import ChatMessage, ChatSession

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_thought_persistence_db(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[None, None, None]:
    """Isolates SQLite DB and restores FastAPI dependency_overrides across runs."""
    db_file = tmp_path / "thought_persistence_test.db"
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
    monkeypatch.setattr(db_session, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(sys.modules[__name__], "SessionLocal", TestingSessionLocal)

    try:
        yield
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(orig_overrides)
        test_engine.dispose()


def test_thought_trace_persistence_and_restoration():
    """Validates that assistant reasoning thoughts and ThoughtLine steps persist to DB and restore via REST API."""
    test_session_id = "sess_thought_persist_test"

    with SessionLocal() as db:
        # Create session if not exists
        sess = db.query(ChatSession).filter(ChatSession.session_id == test_session_id).first()
        if not sess:
            sess = ChatSession(session_id=test_session_id, user_id="u_persist_test", title="深度思考持久化测试")
            db.add(sess)

        # Insert assistant message with thought trace
        msg = ChatMessage(
            session_id=test_session_id,
            role="assistant",
            content="[RAG Answer]: 单次借用最长 14 天。",
            sources='["03_IT_运维与资产借用指南.md"]',
            thought="Thinking Process: 1. Analyze Request... 2. Review SOP...",
            duration_seconds=3.5,
            thought_steps='["意图理解与业务范畴分析", "调取企业规章与制度知识库", "语义重排并匹配核心条款"]',
        )
        db.add(msg)
        db.commit()

    # Query via REST API
    resp = client.get(f"/api/v1/chat/sessions/{test_session_id}/messages")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    target = data[-1]

    assert target["role"] == "assistant"
    assert target["thought"] == "Thinking Process: 1. Analyze Request... 2. Review SOP..."
    assert target["duration_seconds"] == 3.5
    assert "意图理解与业务范畴分析" in target["thought_steps"]
    assert "调取企业规章与制度知识库" in target["thought_steps"]
