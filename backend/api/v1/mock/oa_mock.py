"""OA Enterprise System Mock REST API Router."""

import random
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from backend.db.session import get_db
from backend.models.ticket import Ticket

router = APIRouter()

SLA_METRICS = {
    "P0": {"response_sla": "< 5 分钟", "resolution_sla": "< 30 分钟", "action": "触发 PagerDuty 电话告警与 CTO 通报"},
    "P1": {"response_sla": "< 15 分钟", "resolution_sla": "< 2 小时", "action": "发送 P1 紧急邮件通报运维经理"},
    "P2": {"response_sla": "< 1 小时", "resolution_sla": "< 8 小时", "action": "分配至值班工程师工单池"},
    "P3": {"response_sla": "< 4 小时", "resolution_sla": "< 24 小时", "action": "标准工单队列处理"},
    "P4": {"response_sla": "< 8 小时", "resolution_sla": "< 48 小时", "action": "日常工单队列处理"}
}


class TicketCreateRequest(BaseModel):
    title: str = Field(..., description="工单标题")
    description: str = Field(..., description="故障或需求描述")
    priority: Optional[str] = Field("P3", description="工单优先级 (P0-P4)")
    department: Optional[str] = Field("IT", description="受理部门")


class EmailSendRequest(BaseModel):
    to_email: str = Field(..., description="收件人邮箱")
    subject: str = Field(..., description="邮件主题")
    body: str = Field(..., description="邮件正文")


@router.post("/tickets")
def create_oa_ticket(
    req: TicketCreateRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Mock OA API: Submit an OA service ticket and persist to Ticket table.
    """
    p_code = (req.priority or "P3").upper()
    if p_code not in SLA_METRICS:
        p_code = "P3"

    ticket_num = random.randint(1000, 9999)
    today_str = datetime.now().strftime("%Y%m%d")
    ticket_id = f"TICK-{today_str}-{ticket_num}"
    sla = SLA_METRICS[p_code]

    t_obj = Ticket(
        ticket_id=ticket_id,
        title=req.title,
        description=req.description,
        priority=p_code,
        department=(req.department or "IT").upper(),
        status="OPEN",
        response_sla=sla["response_sla"],
        resolution_sla=sla["resolution_sla"],
        action_taken=sla["action"],
        created_at=datetime.utcnow()
    )
    db.add(t_obj)
    db.commit()
    db.refresh(t_obj)

    return {
        "status": "SUCCESS",
        "ticket_id": t_obj.ticket_id,
        "title": t_obj.title,
        "description": t_obj.description,
        "priority": t_obj.priority,
        "department": t_obj.department,
        "ticket_status": t_obj.status,
        "response_sla": t_obj.response_sla,
        "resolution_sla": t_obj.resolution_sla,
        "action_taken": t_obj.action_taken,
        "created_at": t_obj.created_at.strftime("%Y-%m-%d %H:%M:%S")
    }


@router.post("/email")
def send_oa_email(
    req: EmailSendRequest
) -> Dict[str, Any]:
    """
    Mock OA API: Send simulated email notification.
    """
    if "@" not in req.to_email:
        return {
            "status": "ERROR",
            "message": f"无效的邮箱地址格式: '{req.to_email}'"
        }

    msg_num = random.randint(100000, 999999)
    message_id = f"MSG-EML-{msg_num}"

    return {
        "status": "SENT",
        "message_id": message_id,
        "to_email": req.to_email,
        "subject": req.subject,
        "body_preview": req.body[:100] + ("..." if len(req.body) > 100 else ""),
        "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
