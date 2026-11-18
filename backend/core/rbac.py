"""Role-Based Access Control (RBAC) & User Security Dependencies."""

from enum import Enum
from typing import Any, Dict, List, Optional
from fastapi import Depends, Header
from pydantic import BaseModel

from backend.core.security import decode_access_token, get_password_hash
from backend.core.exceptions import AuthenticationError, PermissionDeniedError


class RoleEnum(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    EMPLOYEE = "employee"


ROLE_LABELS: Dict[RoleEnum, str] = {
    RoleEnum.ADMIN: "系统管理员",
    RoleEnum.MANAGER: "部门主管",
    RoleEnum.EMPLOYEE: "普通员工",
}


class UserPayload(BaseModel):
    username: str
    display_name: str = ""
    role: RoleEnum
    department: str = "Engineering"
    role_label: str = ""


# Initial Bootstrap Seed Users (In-Memory Demo/Dev User Directory)
MOCK_USERS_DB: Dict[str, Dict[str, Any]] = {
    "employee": {
        "username": "employee",
        "display_name": "林小晴",
        "hashed_password": get_password_hash("emp123"),
        "role": RoleEnum.EMPLOYEE,
        "role_label": ROLE_LABELS[RoleEnum.EMPLOYEE],
        "department": "人力资源部",
    },
    "manager": {
        "username": "manager",
        "display_name": "陈志远",
        "hashed_password": get_password_hash("manager123"),
        "role": RoleEnum.MANAGER,
        "role_label": ROLE_LABELS[RoleEnum.MANAGER],
        "department": "采购管理部",
    },
    "admin": {
        "username": "admin",
        "display_name": "周明辉",
        "hashed_password": get_password_hash("admin123"),
        "role": RoleEnum.ADMIN,
        "role_label": ROLE_LABELS[RoleEnum.ADMIN],
        "department": "IT 系统管理部",
    },
}


def get_demo_identities() -> List[Dict[str, str]]:
    """Returns non-sensitive demo identity metadata for dev/demo role switching."""
    return [
        {
            "username": user["username"],
            "display_name": user["display_name"],
            "role": user["role"].value,
            "role_label": user["role_label"],
            "department": user["department"],
        }
        for user in MOCK_USERS_DB.values()
    ]


def resolve_user_from_token(token: str) -> UserPayload:
    """Decodes a raw JWT token string and builds a validated UserPayload."""
    payload = decode_access_token(token)
    if not payload or "sub" not in payload or "role" not in payload:
        raise AuthenticationError("Invalid or expired JWT access token")

    try:
        role_enum = RoleEnum(payload["role"])
    except ValueError as exc:
        raise AuthenticationError("Invalid user role in access token") from exc

    username = payload["sub"]
    seed_user = MOCK_USERS_DB.get(username, {})
    display_name = payload.get("display_name") or seed_user.get("display_name") or username
    department = payload.get("department") or seed_user.get("department") or "General"
    role_label = payload.get("role_label") or seed_user.get("role_label") or ROLE_LABELS.get(role_enum, role_enum.value)

    return UserPayload(
        username=username,
        display_name=display_name,
        role=role_enum,
        department=department,
        role_label=role_label,
    )


def _extract_user_from_header(authorization: str) -> UserPayload:
    """Parses Bearer JWT Authorization header and builds a validated UserPayload."""
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthenticationError("Invalid Authorization header format. Expected 'Bearer <token>'")

    return resolve_user_from_token(parts[1])


async def get_current_user(authorization: Optional[str] = Header(None)) -> UserPayload:
    """Extracts and verifies JWT token from Authorization header."""
    if not authorization:
        raise AuthenticationError("Authorization header is missing")

    return _extract_user_from_header(authorization)


async def get_optional_current_user(authorization: Optional[str] = Header(None)) -> Optional[UserPayload]:
    """Extracts JWT user if Authorization header is provided; returns None when absent."""
    if not authorization:
        return None

    return _extract_user_from_header(authorization)


def require_role(allowed_roles: List[RoleEnum]):
    """Factory dependency for RBAC role checking."""
    async def role_checker(current_user: UserPayload = Depends(get_current_user)) -> UserPayload:
        if current_user.role not in allowed_roles:
            raise PermissionDeniedError(
                f"User role '{current_user.role.value}' is not authorized. Required: {[r.value for r in allowed_roles]}"
            )
        return current_user

    return role_checker
