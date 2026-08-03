"""HR Enterprise System Mock REST API Router."""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.db.session import get_db
from backend.models.user import User
from backend.db.seed import seed_initial_data

router = APIRouter()


@router.get("/employees/{id_or_name}")
def get_employee_by_id_or_name(
    id_or_name: str,
    department: Optional[str] = None,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Mock HR API: Query employee details by employee_id or name.
    """
    seed_initial_data(db)

    query = db.query(User).filter(
        (User.employee_id == id_or_name) | (User.name.like(f"%{id_or_name}%"))
    )
    if department:
        query = query.filter(User.department.like(f"%{department}%"))

    users = query.all()
    if not users:
        return {
            "status": "NOT_FOUND",
            "count": 0,
            "message": f"未找到员工: '{id_or_name}'"
        }

    data = [
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

    return {
        "status": "SUCCESS",
        "count": len(data),
        "data": data
    }


@router.get("/employees")
def list_employees(
    department: Optional[str] = None,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Mock HR API: List all employees or filter by department.
    """
    seed_initial_data(db)

    query = db.query(User)
    if department:
        query = query.filter(User.department.like(f"%{department}%"))

    users = query.all()
    data = [
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
    return {
        "status": "SUCCESS",
        "count": len(data),
        "data": data
    }
