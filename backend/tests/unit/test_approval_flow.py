"""Unit Tests for Human-in-the-Loop Approval Flow & Three-Layer AI Abort Mechanism."""

import asyncio
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from langchain_core.messages import HumanMessage

from backend.main import app
from backend.db.session import Base, get_db
from backend.models.approval import Approval
from backend.graph.workflow import graph
from backend.graph.state import AgentState
from backend.core.task_manager import task_manager
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


@pytest.mark.asyncio
async def test_langgraph_interrupt_on_high_value_purchase(setup_test_database):
    """Tests that LangGraph pauses execution via interrupt() when purchase amount > 5,000 RMB."""
    config = {"configurable": {"thread_id": "thread_interrupt_test_001"}}
    initial_state: AgentState = {
        "messages": [HumanMessage(content="申请大额设备采购：MacBook Pro 16 1台，单价 22999 元")],
        "intent": "approval",
        "metadata": {
            "thread_id": "thread_interrupt_test_001",
            "purchase_args": {
                "item_name": "MacBook Pro 16",
                "quantity": 1,
                "unit_price": 22999.0,
                "department": "研发部",
                "reason": "AI 开发高配置要求"
            }
        }
    }

    # Run graph until interrupt
    try:
        await graph.ainvoke(initial_state, config=config)
    except Exception:
        pass

    # Check graph state is paused
    state = graph.get_state(config)
    assert state is not None
    assert state.next == ("approval",)  # Next node to execute when resumed

    # Verify pending Approval record was created in database
    db = setup_test_database
    pending_app = db.query(Approval).filter(Approval.thread_id == "thread_interrupt_test_001").first()
    assert pending_app is not None
    assert pending_app.status == "PENDING"
    assert pending_app.total_price == 22999.0


@pytest.mark.asyncio
async def test_approval_action_api_approve_and_resume(setup_test_database):
    """Tests POST /api/v1/approval/action API approving and resuming LangGraph execution."""
    thread_id = "thread_approve_api_test"
    config = {"configurable": {"thread_id": thread_id}}
    initial_state: AgentState = {
        "messages": [HumanMessage(content="申请采购服务器集群，总价 85000 元")],
        "intent": "approval",
        "metadata": {
            "thread_id": thread_id,
            "purchase_args": {
                "item_name": "Dell R760",
                "quantity": 1,
                "unit_price": 85000.0,
                "department": "IT运维部"
            }
        }
    }

    # Pause graph at interrupt
    try:
        await graph.ainvoke(initial_state, config=config)
    except Exception:
        pass

    db = setup_test_database
    app_record = db.query(Approval).filter(Approval.thread_id == thread_id).first()
    assert app_record is not None
    approval_id = app_record.approval_id

    # Call Approval API with 'approve' action
    payload = {
        "approval_id": approval_id,
        "action": "approve",
        "comment": "预算审核符合要求，准予采购"
    }
    resp = client.post("/api/v1/approval/action", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["db_status"] == "APPROVED"

    # Verify DB record updated
    db.refresh(app_record)
    assert app_record.status == "APPROVED"


@pytest.mark.asyncio
async def test_approval_action_api_reject_and_resume(setup_test_database):
    """Tests POST /api/v1/approval/action API rejecting and resuming LangGraph execution."""
    thread_id = "thread_reject_api_test"
    config = {"configurable": {"thread_id": thread_id}}
    initial_state: AgentState = {
        "messages": [HumanMessage(content="申请采购 10 台办公椅，单价 9800 元")],
        "intent": "approval",
        "metadata": {
            "thread_id": thread_id,
            "purchase_args": {
                "item_name": "Herman Miller 办公椅",
                "quantity": 10,
                "unit_price": 9800.0,
                "department": "行政后勤部"
            }
        }
    }

    try:
        await graph.ainvoke(initial_state, config=config)
    except Exception:
        pass

    db = setup_test_database
    app_record = db.query(Approval).filter(Approval.thread_id == thread_id).first()
    assert app_record is not None

    # Call Approval API with 'reject' action
    resp = client.post("/api/v1/approval/action", json={"approval_id": app_record.approval_id, "action": "reject"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["db_status"] == "REJECTED"


@pytest.mark.asyncio
async def test_three_layer_chat_abort_api():
    """Tests Three-Layer AI Abort API POST /api/v1/chat/abort."""
    thread_id = "thread_abort_test_001"
    config = {"configurable": {"thread_id": thread_id}}

    initial_state: AgentState = {
        "messages": [HumanMessage(content="流式生成测试问答需求")],
        "user_id": "u_abort",
        "session_id": "s_abort",
        "metadata": {"status": "RUNNING"}
    }
    await graph.ainvoke(initial_state, config=config)

    async def mock_long_task():
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            pass

    task = asyncio.create_task(mock_long_task())
    task_manager.register_task(thread_id, task)

    resp = client.post("/api/v1/chat/abort", json={"thread_id": thread_id})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"

    await asyncio.sleep(0.05)
    assert task.cancelled() is True or task.done() is True
