"""Unit Tests for Enterprise Mock Systems (HR / ERP / OA) and SQLAlchemy Persistence."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from backend.main import app
from backend.db.session import Base, get_db
from backend.models.user import User
from backend.models.inventory import Inventory
from backend.models.ticket import Ticket
from backend.models.purchase import Purchase
from backend.db.seed import seed_initial_data
from backend.tools.impl import create_ticket, create_purchase

# Setup In-Memory SQLite Test Engine with StaticPool for thread-safe shared connection
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_test_database():
    """Creates database tables and seeds initial data before each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    seed_initial_data(db)
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


def override_get_db():
    """Dependency override for test DB session."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_sqlalchemy_models_crud_operations(setup_test_database):
    """Tests SQLAlchemy ORM models User, Inventory, Ticket, Purchase CRUD."""
    db = setup_test_database

    # 1. User
    users = db.query(User).filter(User.name == "张伟").all()
    assert len(users) == 1
    assert users[0].department == "IT运维部"

    # 2. Inventory
    items = db.query(Inventory).filter(Inventory.item_name.like("%MacBook%")).all()
    assert len(items) == 1
    assert items[0].unit_price == 22999.0

    # 3. Ticket
    ticket = Ticket(
        ticket_id="TICK-TEST-001",
        title="网络监控告警",
        description="交换机端口丢包",
        priority="P1",
        department="IT",
        status="OPEN",
        response_sla="< 15 分钟"
    )
    db.add(ticket)
    db.commit()

    saved_ticket = db.query(Ticket).filter(Ticket.ticket_id == "TICK-TEST-001").first()
    assert saved_ticket is not None
    assert saved_ticket.priority == "P1"

    # 4. Purchase
    purchase = Purchase(
        purchase_id="PO-TEST-001",
        item_name="Dell 显示器",
        quantity=5,
        unit_price=3499.0,
        total_price=17495.0,
        department="研发部",
        reason="团队扩建需求",
        approval_status="PENDING_SUPERVISOR_APPROVAL"
    )
    db.add(purchase)
    db.commit()

    saved_po = db.query(Purchase).filter(Purchase.purchase_id == "PO-TEST-001").first()
    assert saved_po is not None
    assert saved_po.total_price == 17495.0


def test_hr_mock_api_get_employee():
    """Tests HR Mock REST API GET /api/v1/mock/hr/employees/{id_or_name}."""
    resp = client.get("/api/v1/mock/hr/employees/张伟")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["count"] >= 1
    assert data["data"][0]["name"] == "张伟"
    assert data["data"][0]["rank"] == "P6"

    # Test List Employees
    resp_list = client.get("/api/v1/mock/hr/employees?department=研发部")
    assert resp_list.status_code == 200
    list_data = resp_list.json()
    assert list_data["status"] == "SUCCESS"
    assert any(emp["name"] == "李娜" for emp in list_data["data"])


def test_erp_mock_api_inventory():
    """Tests ERP Mock REST API GET /api/v1/mock/erp/inventory."""
    resp = client.get("/api/v1/mock/erp/inventory?item_name=MacBook")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["count"] >= 1
    assert data["data"][0]["unit_price"] == 22999.0


def test_erp_mock_api_create_purchase():
    """Tests ERP Mock REST API POST /api/v1/mock/erp/purchases."""
    payload = {
        "item_name": "MacBook Pro 16",
        "quantity": 2,
        "unit_price": 22999.0,
        "department": "研发部",
        "reason": "新项目组研发拓展"
    }
    resp = client.post("/api/v1/mock/erp/purchases", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["purchase_id"].startswith("PO-")
    assert data["total_price"] == 45998.0
    assert data["approval_status"] == "PENDING_SUPERVISOR_APPROVAL"


def test_oa_mock_api_create_ticket():
    """Tests OA Mock REST API POST /api/v1/mock/oa/tickets."""
    payload = {
        "title": "防火墙规则变更请求",
        "description": "允许 8443 端口出站流量",
        "priority": "P2",
        "department": "IT"
    }
    resp = client.post("/api/v1/mock/oa/tickets", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    assert data["ticket_id"].startswith("TICK-")
    assert data["response_sla"] == "< 1 小时"


def test_oa_mock_api_send_email():
    """Tests OA Mock REST API POST /api/v1/mock/oa/email."""
    payload = {
        "to_email": "lina@company.com",
        "subject": "代码审查提醒",
        "body": "请及时审核 PR #1024 相关的 CI/CD 构建变动。"
    }
    resp = client.post("/api/v1/mock/oa/email", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SENT"
    assert data["message_id"].startswith("MSG-EML-")


def test_tools_integration():
    """Tests Tool execution creating tickets and purchases."""
    t_res = create_ticket(title="系统磁盘爆满", description="根目录使用率 99%", priority="P1")
    assert t_res["status"] == "SUCCESS"
    assert t_res["ticket_id"].startswith("TICK-")
    assert t_res["priority"] == "P1"

    p_res = create_purchase(item_name="ThinkPad X1", quantity=1, unit_price=14999.0, department="IT运维部")
    assert p_res["status"] == "SUCCESS"
    assert p_res["approval_status"] == "PENDING_SUPERVISOR_APPROVAL"
