"""Unit Tests for JWT Authentication & RBAC Permission Middleware."""

from fastapi.testclient import TestClient
from backend.main import app
from backend.core.security import get_password_hash, verify_password, create_access_token, decode_access_token

client = TestClient(app)


def test_password_hashing():
    """Tests password hashing and verification."""
    password = "secret_password_123"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed) is True
    assert verify_password("wrong_password", hashed) is False


def test_jwt_token_encoding_decoding():
    """Tests JWT access token creation and decoding."""
    data = {"sub": "test_user", "role": "admin"}
    token = create_access_token(data)
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "test_user"
    assert decoded["role"] == "admin"


def test_login_success():
    """Tests POST /api/v1/auth/login with valid credentials."""
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert "access_token" in body["data"]
    assert body["data"]["role"] == "admin"


def test_login_failure():
    """Tests POST /api/v1/auth/login with invalid credentials."""
    response = client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrongpassword"})
    assert response.status_code == 401
    body = response.json()
    assert body["code"] == 401
    assert "Invalid username or password" in body["message"]


def test_rbac_access_control():
    """Tests RBAC role permission checks."""
    # 1. Login as employee
    emp_login = client.post("/api/v1/auth/login", json={"username": "employee", "password": "emp123"})
    emp_token = emp_login.json()["data"]["access_token"]
    emp_headers = {"Authorization": f"Bearer {emp_token}"}

    # Access /me
    me_resp = client.get("/api/v1/auth/me", headers=emp_headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["data"]["username"] == "employee"

    # Employee accesses admin-only endpoint -> 403 Forbidden
    admin_resp = client.get("/api/v1/auth/admin-only", headers=emp_headers)
    assert admin_resp.status_code == 403
    assert admin_resp.json()["code"] == 403

    # 2. Login as admin
    admin_login = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    admin_token = admin_login.json()["data"]["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Admin accesses admin-only endpoint -> 200 OK
    admin_resp_2 = client.get("/api/v1/auth/admin-only", headers=admin_headers)
    assert admin_resp_2.status_code == 200
    assert "Welcome Admin admin" in admin_resp_2.json()["data"]["message"]
