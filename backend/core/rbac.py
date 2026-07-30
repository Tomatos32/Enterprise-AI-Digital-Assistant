"""Role-Based Access Control (RBAC) & User Security Dependencies."""

from enum import Enum
from typing import List, Optional
from fastapi import Depends, Header
from pydantic import BaseModel

from backend.core.security import decode_access_token, get_password_hash
from backend.core.exceptions import AuthenticationError, PermissionDeniedError


class RoleEnum(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    EMPLOYEE = "employee"


class UserPayload(BaseModel):
    username: str
    role: RoleEnum
    department: str = "Engineering"


# Initial Bootstrap Seed Users (In-Memory for Sprint 1 Mock/Testing)
MOCK_USERS_DB = {
    "admin": {
        "username": "admin",
        "hashed_password": get_password_hash("admin123"),
        "role": RoleEnum.ADMIN,
        "department": "IT Management"
    },
    "manager": {
        "username": "manager",
        "hashed_password": get_password_hash("manager123"),
        "role": RoleEnum.MANAGER,
        "department": "Procurement"
    },
    "employee": {
        "username": "employee",
        "hashed_password": get_password_hash("emp123"),
        "role": RoleEnum.EMPLOYEE,
        "department": "HR"
    }
}


async def get_current_user(authorization: Optional[str] = Header(None)) -> UserPayload:
    """Extracts and verifies JWT token from Authorization header."""
    if not authorization:
        raise AuthenticationError("Authorization header is missing")
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthenticationError("Invalid Authorization header format. Expected 'Bearer <token>'")

    token = parts[1]
    payload = decode_access_token(token)
    if not payload or "sub" not in payload or "role" not in payload:
        raise AuthenticationError("Invalid or expired JWT access token")

    return UserPayload(
        username=payload["sub"],
        role=RoleEnum(payload["role"]),
        department=payload.get("department", "General")
    )


def require_role(allowed_roles: List[RoleEnum]):
    """Factory dependency for RBAC role checking."""
    async def role_checker(current_user: UserPayload = Depends(get_current_user)) -> UserPayload:
        if current_user.role not in allowed_roles:
            raise PermissionDeniedError(
                f"User role '{current_user.role.value}' is not authorized. Required: {[r.value for r in allowed_roles]}"
            )
        return current_user

    return role_checker
