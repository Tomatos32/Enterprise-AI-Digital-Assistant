"""Email Notification Dispatch Tool Implementation."""

import random
from datetime import datetime
from typing import Dict, Any
from backend.tools.registry import register_tool


@register_tool(
    name="send_email",
    description="发送电子邮件通知给员工、主管或外部供应商",
    parameters={
        "type": "object",
        "properties": {
            "to_email": {"type": "string", "description": "收件人邮箱地址 (例如: zhangwei@company.com)"},
            "subject": {"type": "string", "description": "邮件主题/标题"},
            "body": {"type": "string", "description": "邮件正文内容"}
        },
        "required": ["to_email", "subject", "body"]
    }
)
def send_email(to_email: str, subject: str, body: str) -> Dict[str, Any]:
    """Simulates sending an email notification."""
    if "@" not in to_email:
        return {
            "status": "ERROR",
            "message": f"无效的邮箱地址格式: '{to_email}'"
        }

    msg_num = random.randint(100000, 999999)
    message_id = f"MSG-EML-{msg_num}"

    return {
        "status": "SENT",
        "message_id": message_id,
        "to_email": to_email,
        "subject": subject,
        "body_preview": body[:100] + ("..." if len(body) > 100 else ""),
        "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
