"""Mock Implementation for Enterprise System Adapters."""

import random
from datetime import datetime
from typing import Optional, Dict, Any

from backend.adapters.base import (
    BaseHRAdapter,
    BaseERPAdapter,
    BaseOAAdapter,
    AdapterHealthStatus,
)
from backend.db.session import SessionLocal
from backend.models.user import User
from backend.models.inventory import Inventory
from backend.models.ticket import Ticket
from backend.models.purchase import Purchase
from backend.db.seed import seed_initial_data

# In-memory fallbacks
MOCK_EMPLOYEES_DATA = [
    {
        "employee_id": "EMP-1001",
        "name": "张伟",
        "department": "IT运维部",
        "title": "资深运维工程师",
        "rank": "P6",
        "email": "zhangwei@company.com",
        "status": "Active",
        "join_date": "2022-03-15"
    },
    {
        "employee_id": "EMP-1002",
        "name": "李娜",
        "department": "研发部",
        "title": "资深后端架构师",
        "rank": "P7",
        "email": "lina@company.com",
        "status": "Active",
        "join_date": "2021-06-10"
    }
]

MOCK_INVENTORY_DATA = [
    {
        "item_id": "DEV-001",
        "item_name": "MacBook Pro 16",
        "spec": "M3 Max / 36G / 1TB",
        "unit_price": 22999.0,
        "stock": 12,
        "department": "IT运维部",
        "status": "In Stock"
    },
    {
        "item_id": "DEV-002",
        "item_name": "Dell UltraSharp 显示器",
        "spec": "27英寸 4K U2723QE",
        "unit_price": 3499.0,
        "stock": 28,
        "department": "行政后勤部",
        "status": "In Stock"
    },
    {
        "item_id": "DEV-003",
        "item_name": "Herman Miller 办公椅",
        "spec": "Aeron 人体工学椅",
        "unit_price": 9800.0,
        "stock": 8,
        "department": "行政后勤部",
        "status": "In Stock"
    },
    {
        "item_id": "DEV-004",
        "item_name": "ThinkPad X1 Carbon",
        "spec": "i7-1370P / 32G / 1TB",
        "unit_price": 14999.0,
        "stock": 15,
        "department": "IT运维部",
        "status": "In Stock"
    },
    {
        "item_id": "DEV-005",
        "item_name": "Logitech MX Master 3S",
        "spec": "无线蓝牙鼠标 8000DPI",
        "unit_price": 699.0,
        "stock": 45,
        "department": "行政后勤部",
        "status": "In Stock"
    }
]

SLA_METRICS = {
    "P0": {"response_sla": "< 5 分钟", "resolution_sla": "< 30 分钟", "action": "触发 PagerDuty 电话告警与 CTO 通报"},
    "P1": {"response_sla": "< 15 分钟", "resolution_sla": "< 2 小时", "action": "发送 P1 紧急邮件通报运维经理"},
    "P2": {"response_sla": "< 1 小时", "resolution_sla": "< 8 小时", "action": "分配至值班工程师工单池"},
    "P3": {"response_sla": "< 4 小时", "resolution_sla": "< 24 小时", "action": "标准工单队列处理"},
    "P4": {"response_sla": "< 8 小时", "resolution_sla": "< 48 小时", "action": "日常工单队列处理"}
}


class MockHRAdapter(BaseHRAdapter):
    """Mock HR Adapter interacting with local DB or fallback in-memory records."""

    def get_employee(self, id_or_name: str, department: Optional[str] = None) -> Dict[str, Any]:
        try:
            with SessionLocal() as db:
                seed_initial_data(db)
                query = db.query(User).filter(
                    (User.employee_id == id_or_name) | (User.name.like(f"%{id_or_name}%"))
                )
                if department:
                    query = query.filter(User.department.like(f"%{department}%"))
                users = query.all()
                if users:
                    return {
                        "status": "SUCCESS",
                        "count": len(users),
                        "data": [
                            {
                                "employee_id": u.employee_id,
                                "name": u.name,
                                "department": u.department,
                                "title": u.title,
                                "rank": u.rank,
                                "email": u.email,
                                "status": u.status,
                                "join_date": u.join_date
                            }
                            for u in users
                        ]
                    }
        except Exception:
            pass

        # Memory Fallback
        matched = [
            e for e in MOCK_EMPLOYEES_DATA
            if id_or_name in e["name"] or id_or_name == e["employee_id"]
        ]
        if department:
            matched = [e for e in matched if department in e["department"]]
        return {
            "status": "SUCCESS" if matched else "NOT_FOUND",
            "count": len(matched),
            "data": matched
        }

    def list_employees(self, department: Optional[str] = None) -> Dict[str, Any]:
        try:
            with SessionLocal() as db:
                seed_initial_data(db)
                query = db.query(User)
                if department:
                    query = query.filter(User.department.like(f"%{department}%"))
                users = query.all()
                return {
                    "status": "SUCCESS",
                    "count": len(users),
                    "data": [
                        {
                            "employee_id": u.employee_id,
                            "name": u.name,
                            "department": u.department,
                            "title": u.title,
                            "rank": u.rank,
                            "email": u.email,
                            "status": u.status
                        }
                        for u in users
                    ]
                }
        except Exception:
            return {"status": "SUCCESS", "count": len(MOCK_EMPLOYEES_DATA), "data": MOCK_EMPLOYEES_DATA}

    async def ping(self) -> AdapterHealthStatus:
        return self.ping_sync()

    def ping_sync(self) -> AdapterHealthStatus:
        return AdapterHealthStatus(
            service_name="HR",
            adapter_type="MOCK",
            status="UP",
            latency_ms=0.5,
            endpoint="local://mock/hr",
            message="Mock HR system running locally"
        )


class MockERPAdapter(BaseERPAdapter):
    """Mock ERP Adapter for inventory lookup and purchase order persistence."""

    def get_inventory(self, item_name: Optional[str] = None, category: Optional[str] = None) -> Dict[str, Any]:
        try:
            with SessionLocal() as db:
                seed_initial_data(db)
                query = db.query(Inventory)
                if item_name:
                    query = query.filter(
                        (Inventory.item_name.like(f"%{item_name}%")) | (Inventory.spec.like(f"%{item_name}%"))
                    )
                if category:
                    query = query.filter(Inventory.department.like(f"%{category}%"))
                items = query.all()
                if items:
                    return {
                        "status": "SUCCESS",
                        "count": len(items),
                        "data": [
                            {
                                "item_id": i.item_id,
                                "item_name": i.item_name,
                                "spec": i.spec,
                                "unit_price": i.unit_price,
                                "stock": i.stock,
                                "department": i.department,
                                "status": i.status
                            }
                            for i in items
                        ]
                    }
        except Exception:
            pass

        # Memory Fallback
        matched = [
            i for i in MOCK_INVENTORY_DATA
            if not item_name or item_name in i["item_name"] or item_name in i.get("spec", "")
        ]
        if category:
            matched = [i for i in matched if category in i.get("department", "")]
        return {
            "status": "SUCCESS" if matched else "NOT_FOUND",
            "count": len(matched),
            "data": matched
        }

    def create_purchase(
        self,
        item_name: str,
        quantity: int,
        unit_price: float,
        department: str,
        reason: str = "办公采购"
    ) -> Dict[str, Any]:
        if quantity <= 0:
            return {"status": "ERROR", "message": "采购数量必须大于 0"}
        if unit_price <= 0:
            return {"status": "ERROR", "message": "预估单价必须大于 0"}

        total_price = round(quantity * unit_price, 2)
        po_num = random.randint(1000, 9999)
        today_str = datetime.now().strftime("%Y%m%d")
        purchase_id = f"PO-{today_str}-{po_num}"

        if total_price <= 5000:
            approval_status = "AUTO_APPROVED"
            approval_node = "系统自动通过"
            action_note = "Agent 直接调用 create_purchase() 提交 ERP"
        elif 5000 < total_price <= 50000:
            approval_status = "PENDING_SUPERVISOR_APPROVAL"
            approval_node = "部门主管审批"
            action_note = "Agent 触发 Interrupt 状态等待主管确认 (Human-in-the-loop)"
        elif 50000 < total_price <= 200000:
            approval_status = "PENDING_EXECUTIVE_APPROVAL"
            approval_node = "主管 + 财务总监 + 采购总监联签"
            action_note = "触发多重会签流程，校验部门季度预算"
        else:
            approval_status = "PENDING_BOARD_APPROVAL"
            approval_node = "主管 + 财务总监 + 法务 VP + CEO + 董事会决议"
            action_note = "强制启动招投标 (RFP)，评审委员会审查"

        try:
            with SessionLocal() as db:
                po_obj = Purchase(
                    purchase_id=purchase_id,
                    item_name=item_name,
                    quantity=quantity,
                    unit_price=unit_price,
                    total_price=total_price,
                    department=department,
                    reason=reason,
                    approval_status=approval_status,
                    approval_node=approval_node,
                    action_note=action_note,
                    created_at=datetime.utcnow()
                )
                db.add(po_obj)
                db.commit()
                db.refresh(po_obj)
                return {
                    "status": "SUCCESS",
                    "purchase_id": po_obj.purchase_id,
                    "item_name": po_obj.item_name,
                    "quantity": po_obj.quantity,
                    "unit_price": po_obj.unit_price,
                    "total_price": po_obj.total_price,
                    "department": po_obj.department,
                    "reason": po_obj.reason,
                    "approval_status": po_obj.approval_status,
                    "approval_node": po_obj.approval_node,
                    "action_note": po_obj.action_note,
                    "created_at": po_obj.created_at.strftime("%Y-%m-%d %H:%M:%S")
                }
        except Exception:
            pass

        return {
            "status": "SUCCESS",
            "purchase_id": purchase_id,
            "item_name": item_name,
            "quantity": quantity,
            "unit_price": unit_price,
            "total_price": total_price,
            "department": department,
            "reason": reason,
            "approval_status": approval_status,
            "approval_node": approval_node,
            "action_note": action_note,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    async def ping(self) -> AdapterHealthStatus:
        return self.ping_sync()

    def ping_sync(self) -> AdapterHealthStatus:
        return AdapterHealthStatus(
            service_name="ERP",
            adapter_type="MOCK",
            status="UP",
            latency_ms=0.6,
            endpoint="local://mock/erp",
            message="Mock ERP system running locally"
        )


class MockOAAdapter(BaseOAAdapter):
    """Mock OA Adapter for tickets and notification dispatch."""

    def create_ticket(
        self,
        title: str,
        description: str,
        priority: str = "P3",
        department: str = "IT"
    ) -> Dict[str, Any]:
        p_code = priority.upper()
        if p_code not in SLA_METRICS:
            p_code = "P3"

        ticket_num = random.randint(1000, 9999)
        today_str = datetime.now().strftime("%Y%m%d")
        ticket_id = f"TICK-{today_str}-{ticket_num}"
        sla = SLA_METRICS[p_code]

        try:
            with SessionLocal() as db:
                t_obj = Ticket(
                    ticket_id=ticket_id,
                    title=title,
                    description=description,
                    priority=p_code,
                    department=department.upper(),
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
        except Exception:
            pass

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

    def send_email(self, to_email: str, subject: str, body: str) -> Dict[str, Any]:
        if "@" not in to_email:
            return {"status": "ERROR", "message": f"无效的邮箱地址格式: '{to_email}'"}

        msg_num = random.randint(100000, 999999)
        message_id = f"MSG-EML-{msg_num}"
        return {
            "status": "SUCCESS",
            "message_id": message_id,
            "to_email": to_email,
            "subject": subject,
            "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "service_provider": "Mock Mail Relay",
            "note": "测试环境模拟邮件投递成功"
        }

    async def ping(self) -> AdapterHealthStatus:
        return self.ping_sync()

    def ping_sync(self) -> AdapterHealthStatus:
        return AdapterHealthStatus(
            service_name="OA",
            adapter_type="MOCK",
            status="UP",
            latency_ms=0.4,
            endpoint="local://mock/oa",
            message="Mock OA system running locally"
        )
