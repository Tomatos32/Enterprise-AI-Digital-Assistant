"""Authentication Router for JWT Token Issuance, Profile & Dev Role Switching."""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.core.config import settings
from backend.core.security import verify_password, create_access_token
from backend.core.rbac import (
    MOCK_USERS_DB,
    RoleEnum,
    UserPayload,
    get_current_user,
    get_demo_identities,
    require_role,
)
from backend.core.exceptions import AppException, AuthenticationError, PermissionDeniedError, StandardResponse

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class RoleSwitchRequest(BaseModel):
    username: Optional[str] = None
    role: Optional[RoleEnum] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str
    display_name: str
    department: str
    role_label: str


def _ensure_demo_switching_enabled() -> None:
    """Allows quick demo role switching only in development/test or mock-enabled deployments."""
    if settings.ENVIRONMENT not in ("development", "test") and not settings.USE_MOCK_SYSTEMS:
        raise PermissionDeniedError("Quick demo role switching is disabled in production mode")


def _issue_token_response(user: Dict[str, Any]) -> TokenResponse:
    """Builds signed JWT access token and standardized user identity payload."""
    token_data = {
        "sub": user["username"],
        "role": user["role"].value,
        "department": user["department"],
        "display_name": user["display_name"],
        "role_label": user["role_label"],
    }
    access_token = create_access_token(data=token_data)
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        role=user["role"].value,
        username=user["username"],
        display_name=user["display_name"],
        department=user["department"],
        role_label=user["role_label"],
    )


@router.post("/login", response_model=StandardResponse)
async def login(body: LoginRequest):
    """Authenticates user and issues JWT access token."""
    user = MOCK_USERS_DB.get(body.username)
    if not user or not verify_password(body.password, user["hashed_password"]):
        raise AuthenticationError("Invalid username or password")

    token_resp = _issue_token_response(user)
    return StandardResponse(data=token_resp.model_dump())


@router.get("/identities", response_model=StandardResponse)
async def list_demo_identities():
    """Returns non-sensitive demo identities for quick role context switching."""
    _ensure_demo_switching_enabled()
    return StandardResponse(data=get_demo_identities())


@router.post("/switch-role", response_model=StandardResponse)
async def switch_demo_role(body: RoleSwitchRequest):
    """Issues a valid JWT token for a target demo identity in dev/demo mode."""
    _ensure_demo_switching_enabled()

    target_user = None
    if body.username:
        target_user = MOCK_USERS_DB.get(body.username)
    elif body.role:
        target_user = next(
            (u for u in MOCK_USERS_DB.values() if u["role"] == body.role),
            None,
        )

    if not target_user:
        raise AppException("Requested demo identity not found", code=404)

    token_resp = _issue_token_response(target_user)
    return StandardResponse(data=token_resp.model_dump())


@router.get("/me", response_model=StandardResponse)
async def get_my_profile(current_user: UserPayload = Depends(get_current_user)):
    """Returns profile of currently authenticated user."""
    return StandardResponse(data=current_user.model_dump())


@router.get("/admin-only", response_model=StandardResponse)
async def admin_only_endpoint(current_user: UserPayload = Depends(require_role([RoleEnum.ADMIN]))):
    """Protected endpoint for Admin role only."""
    return StandardResponse(data={"message": f"Welcome Admin {current_user.username}"})
