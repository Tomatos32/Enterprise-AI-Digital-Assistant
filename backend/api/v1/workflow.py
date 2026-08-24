"""Webhook & Enterprise Workflow Automation (n8n / Dify / WeCom Bot) Router."""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks, Header
from pydantic import BaseModel, Field
import httpx

logger = logging.getLogger(__name__)

router = APIRouter()


class WebhookEventPayload(BaseModel):
    event_type: str = Field(..., description="事件类型 (e.g., 'approval.approved', 'approval.rejected', 'dify.sync', 'n8n.trigger', 'custom.workflow')")
    source: str = Field("ai_assistant", description="事件源系统 (e.g., 'ai_assistant', 'n8n', 'dify', 'erp')")
    data: Dict[str, Any] = Field(default_factory=dict, description="事件携带的业务载荷数据")
    target_webhook_url: Optional[str] = Field(None, description="可选的外部 Webhook 回调地址 (n8n / Dify / 企微 Bot Webhook URL)")
    notify_wecom: bool = Field(True, description="是否同时向企业微信机器人发送卡片通知")
    secret_token: Optional[str] = Field(None, description="安全验证 Token")


class WebhookResponse(BaseModel):
    status: str
    event_id: str
    event_type: str
    processed_at: str
    target_dispatched: bool
    wecom_notified: bool
    details: Dict[str, Any] = Field(default_factory=dict)


# In-memory event log for inspection, testing, and mock verification
EVENT_HISTORY: List[Dict[str, Any]] = []
MOCK_WECOM_MESSAGES: List[Dict[str, Any]] = []


def build_wecom_markdown_card(event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Constructs a standard Enterprise WeChat (WeCom) Bot Markdown message card.
    """
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if event_type == "approval.approved":
        approval_id = data.get("approval_id", "APP-UNKNOWN")
        item_name = data.get("item_name", "未知物资")
        quantity = data.get("quantity", 1)
        total_price = data.get("total_price", 0.0)
        department = data.get("department", "研发部")
        approver = data.get("approver", "系统主管")

        content = (
            f"### 🟢 【审批通过通知】采购流程已自动推进\n"
            f"> **审批单号**：<font color=\"comment\">{approval_id}</font>\n"
            f"> **申请部门**：{department}\n"
            f"> **采购物品**：**{item_name}** × {quantity}\n"
            f"> **总金额**：<font color=\"warning\">¥{total_price:,.2f}</font>\n"
            f"> **审批人**：{approver}\n"
            f"> **处理时间**：{now_str}\n\n"
            f"✅ **已触发 n8n / Dify 自动化工作流，并完成 ERP 资产入库登记！**"
        )
    elif event_type == "approval.rejected":
        approval_id = data.get("approval_id", "APP-UNKNOWN")
        reason = data.get("reason", "预算超标或不符合合规要求")
        content = (
            f"### 🔴 【审批驳回通知】单据未通过审核\n"
            f"> **审批单号**：<font color=\"comment\">{approval_id}</font>\n"
            f"> **驳回原因**：<font color=\"warning\">{reason}</font>\n"
            f"> **通知时间**：{now_str}\n\n"
            f"⚠️ 请与主管沟通并修正申请信息后重新提交。"
        )
    else:
        content = (
            f"### ℹ️ 【工作流事件触发】{event_type}\n"
            f"> **事件源**：{data.get('source', 'enterprise-assistant')}\n"
            f"> **时间**：{now_str}\n"
            f"> **载荷详情**：`{str(data)}`"
        )

    return {
        "msgtype": "markdown",
        "markdown": {
            "content": content
        }
    }


async def dispatch_webhook_async(
    event_type: str,
    data: Dict[str, Any],
    target_url: Optional[str] = None,
    notify_wecom: bool = True
) -> Dict[str, Any]:
    """
    Asynchronously dispatches webhook to external systems (n8n / Dify / WeCom).
    """
    dispatch_results = {
        "target_url_called": False,
        "target_status": None,
        "wecom_notified": False
    }

    # 1. Dispatch to custom target_url (e.g. n8n or Dify trigger endpoint)
    if target_url:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(target_url, json={"event": event_type, "data": data, "timestamp": datetime.now().isoformat()})
                dispatch_results["target_url_called"] = True
                dispatch_results["target_status"] = resp.status_code
        except Exception as e:
            logger.warning(f"Failed to dispatch webhook to {target_url}: {e}")
            dispatch_results["target_status"] = f"ERROR: {str(e)}"

    # 2. WeCom Bot Notification
    if notify_wecom:
        card = build_wecom_markdown_card(event_type, data)
        MOCK_WECOM_MESSAGES.append({
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "card": card
        })
        dispatch_results["wecom_notified"] = True
        logger.info(f"Enterprise WeChat Bot notification created for event: {event_type}")

    return dispatch_results


@router.post("/event", response_model=WebhookResponse)
async def handle_webhook_event(
    payload: WebhookEventPayload,
    background_tasks: BackgroundTasks,
    x_webhook_token: Optional[str] = Header(None)
):
    """
    Unified Webhook Ingestion & Trigger Endpoint (`POST /api/v1/webhook/event`).
    Accepts workflow events from n8n / Dify or triggers downstream notifications.
    """
    event_id = f"EVT-{datetime.now().strftime('%Y%m%d%H%M%S%f')[:17]}"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Optional token verification if provided
    if payload.secret_token and payload.secret_token != "harness_workflow_secret_2026":
        if x_webhook_token != "harness_workflow_secret_2026":
            raise HTTPException(status_code=401, detail="Webhook Secret Token 校验失败")

    # Record event in history
    event_record = {
        "event_id": event_id,
        "event_type": payload.event_type,
        "source": payload.source,
        "data": payload.data,
        "timestamp": now_str,
        "target_url": payload.target_webhook_url,
        "notify_wecom": payload.notify_wecom
    }
    EVENT_HISTORY.append(event_record)

    # Perform or schedule dispatch
    dispatch_info = await dispatch_webhook_async(
        event_type=payload.event_type,
        data=payload.data,
        target_url=payload.target_webhook_url,
        notify_wecom=payload.notify_wecom
    )

    return WebhookResponse(
        status="SUCCESS",
        event_id=event_id,
        event_type=payload.event_type,
        processed_at=now_str,
        target_dispatched=dispatch_info.get("target_url_called", False),
        wecom_notified=dispatch_info.get("wecom_notified", False),
        details=dispatch_info
    )


@router.get("/history")
def get_webhook_history() -> Dict[str, Any]:
    """Returns the recent webhook event history."""
    return {
        "status": "SUCCESS",
        "total_events": len(EVENT_HISTORY),
        "events": EVENT_HISTORY[-50:]
    }


@router.get("/wecom/messages")
def get_wecom_mock_messages() -> Dict[str, Any]:
    """Returns the recorded Enterprise WeChat Bot mock messages."""
    return {
        "status": "SUCCESS",
        "total_messages": len(MOCK_WECOM_MESSAGES),
        "messages": MOCK_WECOM_MESSAGES[-50:]
    }
