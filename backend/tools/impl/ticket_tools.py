"""Service Ticket Creation Tool Implementation."""

import random
from datetime import datetime
from typing import Dict, Any
from backend.tools.registry import register_tool

# SLA response metrics matching DOC-IT-2026-003 SOP
SLA_METRICS = {
    "P0": {"response_sla": "< 5 分钟", "resolution_sla": "< 30 分钟", "action": "触发 PagerDuty 电话告警与 CTO 通报"},
    "P1": {"response_sla": "< 15 分钟", "resolution_sla": "< 2 小时", "action": "发送 P1 紧急邮件通报运维经理"},
    "P2": {"response_sla": "< 1 小时", "resolution_sla": "< 8 小时", "action": "分配至值班工程师工单池"},
    "P3": {"response_sla": "< 4 小时", "resolution_sla": "< 24 小时", "action": "标准工单队列处理"},
    "P4": {"response_sla": "< 8 小时", "resolution_sla": "< 48 小时", "action": "日常工单队列处理"}
}


@register_tool(
    name="create_ticket",
    description="提交 IT 运维或 HR 服务工单，并返回工单编号及 SLA 服务响应承诺",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "工单简短标题 (例如: 核心网络瘫痪, 软件密码重置)"},
            "description": {"type": "string", "description": "工单详细故障或需求描述"},
            "priority": {"type": "string", "description": "故障等级 (P0 灾难, P1 紧急, P2 重要, P3 一般, P4 咨询), 默认为 P3"},
            "department": {"type": "string", "description": "受理部门 (IT 或 HR), 默认为 IT"}
        },
        "required": ["title", "description"]
    }
)
def create_ticket(
    title: str,
    description: str,
    priority: str = "P3",
    department: str = "IT"
) -> Dict[str, Any]:
    """Creates a new service ticket with SLA tracking."""
    p_code = priority.upper()
    if p_code not in SLA_METRICS:
        p_code = "P3"

    ticket_num = random.randint(1000, 9999)
    today_str = datetime.now().strftime("%Y%m%d")
    ticket_id = f"TICK-{today_str}-{ticket_num}"
    sla = SLA_METRICS[p_code]

    return {
        "status": "SUCCESS",
        "ticket_id": ticket_id,
        "title": title,
        "description": description,
        "priority": p_code,
        "department": department.upper(),
        "ticket_status": "OPEN",
        "response_sla": sla["response_sla"],
        "resolution_sla": sla["resolution_sla"],
        "action_taken": sla["action"],
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
