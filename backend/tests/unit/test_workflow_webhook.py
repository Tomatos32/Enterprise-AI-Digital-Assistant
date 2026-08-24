"""Unit Tests for Webhook & Enterprise Workflow Automation (n8n / Dify / WeCom Bot)."""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.api.v1.workflow import (
    build_wecom_markdown_card,
    dispatch_webhook_async,
    EVENT_HISTORY,
    MOCK_WECOM_MESSAGES
)


@pytest.fixture
def client():
    return TestClient(app)


def test_build_wecom_markdown_card_approved():
    """Test building Enterprise WeChat Markdown Card for approved ticket."""
    data = {
        "approval_id": "APP-20260824-001",
        "item_name": "MacBook Pro M3",
        "quantity": 5,
        "total_price": 80000.0,
        "department": "研发部",
        "approver": "张主管"
    }
    card = build_wecom_markdown_card("approval.approved", data)
    assert card["msgtype"] == "markdown"
    assert "APP-20260824-001" in card["markdown"]["content"]
    assert "MacBook Pro M3" in card["markdown"]["content"]
    assert "¥80,000.00" in card["markdown"]["content"]
    assert "n8n / Dify" in card["markdown"]["content"]


def test_build_wecom_markdown_card_rejected():
    """Test building Enterprise WeChat Markdown Card for rejected ticket."""
    data = {
        "approval_id": "APP-20260824-002",
        "reason": "超出部门年度设备预算"
    }
    card = build_wecom_markdown_card("approval.rejected", data)
    assert card["msgtype"] == "markdown"
    assert "APP-20260824-002" in card["markdown"]["content"]
    assert "超出部门年度设备预算" in card["markdown"]["content"]


@pytest.mark.asyncio
async def test_dispatch_webhook_async_mock():
    """Test asynchronous dispatching to mock WeCom bot."""
    MOCK_WECOM_MESSAGES.clear()
    res = await dispatch_webhook_async(
        event_type="approval.approved",
        data={"approval_id": "APP-TEST-999", "item_name": "Dell 4K 显示器", "total_price": 5998.0},
        notify_wecom=True
    )
    assert res["wecom_notified"] is True
    assert len(MOCK_WECOM_MESSAGES) == 1
    assert "APP-TEST-999" in MOCK_WECOM_MESSAGES[0]["card"]["markdown"]["content"]


def test_webhook_event_endpoint_success(client):
    """Test POST /api/v1/webhook/event endpoint."""
    EVENT_HISTORY.clear()
    payload = {
        "event_type": "dify.sync",
        "source": "dify_cloud",
        "data": {"workflow_id": "wf_12345", "status": "COMPLETED", "result": "Sync OK"},
        "notify_wecom": True,
        "secret_token": "harness_workflow_secret_2026"
    }
    response = client.post("/api/v1/webhook/event", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "SUCCESS"
    assert res_data["event_type"] == "dify.sync"
    assert res_data["wecom_notified"] is True
    assert len(EVENT_HISTORY) >= 1


def test_webhook_event_endpoint_unauthorized(client):
    """Test POST /api/v1/webhook/event with invalid secret token."""
    payload = {
        "event_type": "custom.workflow",
        "source": "untrusted_source",
        "data": {"action": "dangerous_call"},
        "secret_token": "wrong_secret"
    }
    response = client.post("/api/v1/webhook/event", json=payload)
    assert response.status_code == 401
    assert "Token" in response.json()["message"]


def test_webhook_history_and_wecom_endpoints(client):
    """Test GET /api/v1/webhook/history and /wecom/messages."""
    resp_hist = client.get("/api/v1/webhook/history")
    assert resp_hist.status_code == 200
    assert "events" in resp_hist.json()

    resp_wecom = client.get("/api/v1/webhook/wecom/messages")
    assert resp_wecom.status_code == 200
    assert "messages" in resp_wecom.json()
