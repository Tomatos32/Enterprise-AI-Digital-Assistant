"""Authentication Router for JWT Token Issuance & User Profile."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.core.security import verify_password, create_access_token
from backend.core.rbac import MOCK_USERS_DB, RoleEnum, UserPayload, get_current_user, require_role
from backend.core.exceptions import AuthenticationError, StandardResponse

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str


@router.post("/login", response_model=StandardResponse)
async def login(body: LoginRequest):
    """Authenticates user and issues JWT access token."""
    user = MOCK_USERS_DB.get(body.username)
    if not user or not verify_password(body.password, user["hashed_password"]):
        raise AuthenticationError("Invalid username or password")

    token_data = {
        "sub": user["username"],
        "role": user["role"].value,
        "department": user["department"]
    }
    access_token = create_access_token(data=token_data)

    token_resp = TokenResponse(
        access_token=access_token,
        token_type="bearer",
        role=user["role"].value,
        username=user["username"]
    )
    return StandardResponse(data=token_resp.model_dump())


@router.get("/me", response_model=StandardResponse)
async def get_my_profile(current_user: UserPayload = Depends(get_current_user)):
    """Returns profile of currently authenticated user."""
    return StandardResponse(data=current_user.model_dump())


@router.get("/admin-only", response_model=StandardResponse)
async def admin_only_endpoint(current_user: UserPayload = Depends(require_role([RoleEnum.ADMIN]))):
    """Protected endpoint for Admin role only."""
    return StandardResponse(data={"message": f"Welcome Admin {current_user.username}"})
