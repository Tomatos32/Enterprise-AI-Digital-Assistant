"""Database Seed Data Generator for User and Inventory Tables."""

from sqlalchemy.orm import Session
from backend.db.session import Base
from backend.models.user import User
from backend.models.inventory import Inventory

DEFAULT_USERS = [
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
    },
    {
        "employee_id": "EMP-1003",
        "name": "王强",
        "department": "行政后勤部",
        "title": "行政经理",
        "rank": "M2",
        "email": "wangqiang@company.com",
        "status": "Active",
        "join_date": "2020-11-01"
    },
    {
        "employee_id": "EMP-1004",
        "name": "陈明",
        "department": "财务部",
        "title": "财务总监",
        "rank": "M3",
        "email": "chenming@company.com",
        "status": "Active",
        "join_date": "2019-04-20"
    },
    {
        "employee_id": "EMP-1005",
        "name": "赵敏",
        "department": "HR部",
        "title": "人力资源总监",
        "rank": "M3",
        "email": "zhaomin@company.com",
        "status": "Active",
        "join_date": "2018-08-12"
    }
]

DEFAULT_INVENTORY = [
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


def seed_initial_data(db: Session):
    """Populates default employee and inventory records if empty, ensuring tables exist."""
    Base.metadata.create_all(bind=db.get_bind())

    # Seed Users
    if db.query(User).count() == 0:
        for u_data in DEFAULT_USERS:
            db.add(User(**u_data))

    # Seed Inventory
    if db.query(Inventory).count() == 0:
        for inv_data in DEFAULT_INVENTORY:
            db.add(Inventory(**inv_data))

    db.commit()
