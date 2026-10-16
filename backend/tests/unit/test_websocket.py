"""Unit Tests for WebSocket Duplex Streaming Channel & Real-time Event Push."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.db.session import Base, get_db
import backend.db.session as db_session_module
import backend.graph.nodes.approval_node as approval_node_module
import backend.api.v1.approval as approval_api_module
import backend.tools.impl.purchase_tools as purchase_tools_module

# Setup In-Memory SQLite Test Engine with StaticPool
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Dependency override for test DB session."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_test_database():
    """Creates database tables before each test and monkeypatches SessionLocal across modules."""
    Base.metadata.create_all(bind=engine)
    db_session_module.SessionLocal = TestingSessionLocal
    approval_node_module.SessionLocal = TestingSessionLocal
    approval_api_module.SessionLocal = TestingSessionLocal
    purchase_tools_module.SessionLocal = TestingSessionLocal
    app.dependency_overrides[get_db] = override_get_db
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)


def test_websocket_connect_and_handshake():
    """Tests WebSocket connection handshake and invalid JSON handling."""
    with client.websocket_connect("/api/v1/ws/chat/client_test_001") as websocket:
        # Send invalid JSON string
        websocket.send_text("Invalid Raw String")
        data = websocket.receive_json()
        assert data["type"] == "error"
        assert data["message"] == "Invalid JSON format"


def test_websocket_chat_streaming_flow():
    """Tests WebSocket duplex chat streaming flow (start -> node_start -> complete)."""
    with client.websocket_connect("/api/v1/ws/chat/client_test_002") as websocket:
        payload = {
            "message": "查询报销SOP标准操作流程与流程门禁",
            "thread_id": "thread_ws_test_002",
            "user_id": "u_ws_test",
            "session_id": "s_ws_test"
        }
        websocket.send_json(payload)

        # 1. Receive Start Handshake Response
        start_frame = websocket.receive_json()
        assert start_frame["type"] == "start"
        assert start_frame["thread_id"] == "thread_ws_test_002"
        assert start_frame["status"] == "PROCESSING"

        received_types = []
        tokens = []
        complete_frame = None

        # Read frames until 'complete' or timeout (streaming tokens can be 50-150 frames)
        for _ in range(200):
            try:
                frame = websocket.receive_json()
                frame_type = frame.get("type")
                received_types.append(frame_type)

                if frame_type == "token":
                    tokens.append(frame.get("content", ""))
                elif frame_type == "complete":
                    complete_frame = frame
                    break
            except Exception:
                break

        assert "node_start" in received_types
        assert "complete" in received_types
        assert complete_frame is not None
        assert len(tokens) > 0 or len(complete_frame.get("final_answer", "")) > 0


def test_websocket_approval_interrupt_event():
    """Tests WebSocket streaming pushing 'interrupt' frame when high-value purchase triggers approval."""
    with client.websocket_connect("/api/v1/ws/chat/client_test_003") as websocket:
        payload = {
            "message": "申请大额设备采购：MacBook Pro 16 1台，单价 22999 元",
            "thread_id": "thread_ws_test_003",
            "user_id": "u_ws_test",
            "session_id": "s_ws_test",
            "metadata": {
                "override_intent": "approval",
                "purchase_args": {
                    "item_name": "MacBook Pro 16",
                    "quantity": 1,
                    "unit_price": 22999.0,
                    "department": "研发部",
                    "reason": "AI 高配置开发"
                }
            }
        }
        websocket.send_json(payload)

        start_frame = websocket.receive_json()
        assert start_frame["type"] == "start"

        received_types = []
        interrupt_frame = None

        for _ in range(30):
            try:
                frame = websocket.receive_json()
                frame_type = frame.get("type")
                received_types.append(frame_type)

                if frame_type == "interrupt":
                    interrupt_frame = frame
                    break
                elif frame_type == "complete":
                    break
            except Exception:
                break

        assert "interrupt" in received_types
        assert interrupt_frame is not None
        assert interrupt_frame["approval_data"]["total_price"] == 22999.0
        assert interrupt_frame["approval_data"]["item_name"] == "MacBook Pro 16"
