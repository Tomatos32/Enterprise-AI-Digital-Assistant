"""Unit tests for Human Feedback (RLHF / DPO) API & Dataset Extraction."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.main import app
from backend.db.session import Base, get_db
from backend.models.feedback import FeedbackRecord
from backend.scripts.extract_dpo_dataset import (
    redact_sensitive_info,
    extract_dpo_pairs_from_records,
)

# Setup In-Memory SQLite Test Engine with StaticPool
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
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
def setup_test_db():
    """Create all tables in memory before each test and drop after."""
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=test_engine)
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


def test_submit_feedback_like_api(client):
    """Test submitting a thumbs-up (like) feedback via POST /api/v1/chat/feedback."""
    payload = {
        "thread_id": "thread-dpo-001",
        "message_id": "msg-001",
        "score": 1,
        "context_snapshot": {
            "prompt": "如何申请年假？",
            "llm_output": "请登录 OA 系统，在【假勤管理】中填写年假申请单并提交主管审批。"
        }
    }
    response = client.post("/api/v1/chat/feedback", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["id"] > 0


def test_submit_feedback_dislike_with_correction_api(client):
    """Test submitting a thumbs-down with user correction."""
    payload = {
        "thread_id": "thread-dpo-002",
        "message_id": "msg-002",
        "score": -1,
        "user_correction": "差旅报销餐标是一类城市 150 元/天，二类城市 100 元/天，不是统一 80 元。",
        "context_snapshot": {
            "prompt": "出差餐补标准是多少？",
            "llm_output": "所有城市出差餐补标准统一为 80 元/天。"
        }
    }
    response = client.post("/api/v1/chat/feedback", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["id"] > 0


def test_submit_feedback_invalid_score(client):
    """Test validation error for invalid scores."""
    payload = {
        "thread_id": "thread-dpo-003",
        "message_id": "msg-003",
        "score": 0,
    }
    response = client.post("/api/v1/chat/feedback", json=payload)
    assert response.status_code == 400


def test_redact_sensitive_info():
    """Test PII masking of phone numbers, emails, and ID cards."""
    text = "联系电话 13812345678，邮箱 test.user@enterprise.com，身份证号 110101199003072345 请尽快办理。"
    masked = redact_sensitive_info(text)
    assert "13812345678" not in masked
    assert "[PHONE_REDACTED]" in masked
    assert "test.user@enterprise.com" not in masked
    assert "[EMAIL_REDACTED]" in masked
    assert "110101199003072345" not in masked
    assert "[ID_CARD_REDACTED]" in masked


def test_extract_dpo_pairs():
    """Test extracting DPO chosen/rejected pairs from feedback records."""
    rec1 = FeedbackRecord(
        id=1,
        thread_id="t1",
        message_id="m1",
        score=-1,
        user_correction="正确答案是 A，请不要选 B，联系电话 13987654321",
        context_snapshot={
            "prompt": "问题 1",
            "llm_output": "错误答案是 B"
        }
    )
    rec2 = FeedbackRecord(
        id=2,
        thread_id="t2",
        message_id="m2",
        score=1,
        user_correction=None,
        context_snapshot={
            "prompt": "问题 2",
            "llm_output": "优质回答内容"
        }
    )

    pairs = extract_dpo_pairs_from_records([rec1, rec2])
    assert len(pairs) == 2

    # Pair 1: Dislike with correction -> correction is chosen
    assert "正确答案是 A" in pairs[0]["chosen"]
    assert "[PHONE_REDACTED]" in pairs[0]["chosen"]
    assert "错误答案是 B" in pairs[0]["rejected"]
    assert pairs[0]["metadata"]["source"] == "dislike_with_correction"

    # Pair 2: Thumbs up -> output is chosen
    assert pairs[1]["chosen"] == "优质回答内容"
    assert pairs[1]["metadata"]["source"] == "thumbs_up_positive"
