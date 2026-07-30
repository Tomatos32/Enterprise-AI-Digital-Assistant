"""Unified Exceptions & Global Error Handling for FastAPI."""

from typing import Any, Optional
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class StandardResponse(BaseModel):
    """Standardized API Response Model."""
    code: int = 200
    message: str = "success"
    data: Optional[Any] = None


class AppException(Exception):
    """Base application domain exception."""
    def __init__(self, message: str, code: int = 400, data: Any = None):
        self.message = message
        self.code = code
        self.data = data
        super().__init__(message)


class AuthenticationError(AppException):
    def __init__(self, message: str = "Invalid authentication credentials"):
        super().__init__(message=message, code=status.HTTP_401_UNAUTHORIZED)


class PermissionDeniedError(AppException):
    def __init__(self, message: str = "Permission denied for requested resource"):
        super().__init__(message=message, code=status.HTTP_403_FORBIDDEN)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Global handler for custom AppException."""
    return JSONResponse(
        status_code=exc.code if exc.code >= 400 and exc.code < 600 else 400,
        content=StandardResponse(
            code=exc.code,
            message=exc.message,
            data=exc.data
        ).model_dump()
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Global handler for FastAPI HTTPException."""
    return JSONResponse(
        status_code=exc.status_code,
        content=StandardResponse(
            code=exc.status_code,
            message=exc.detail if isinstance(exc.detail, str) else "HTTP Exception",
            data=exc.detail if not isinstance(exc.detail, str) else None
        ).model_dump()
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Fallback handler for unhandled server exceptions."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=StandardResponse(
            code=500,
            message="Internal server error",
            data=str(exc)
        ).model_dump()
    )
