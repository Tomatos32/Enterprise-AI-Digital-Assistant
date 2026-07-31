"""Main FastAPI Application Entry Point."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from backend.core.config import settings
from backend.core.exceptions import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    generic_exception_handler,
)
from backend.api.v1.health import router as health_router
from backend.api.v1.auth import router as auth_router
from backend.api.v1.knowledge import router as knowledge_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Exception Handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Set CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(health_router, prefix=settings.API_V1_STR, tags=["Health"])
app.include_router(auth_router, prefix=f"{settings.API_V1_STR}/auth", tags=["Auth & RBAC"])
app.include_router(knowledge_router, prefix=f"{settings.API_V1_STR}/knowledge", tags=["Knowledge Base"])


@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "docs": "/docs",
        "health": f"{settings.API_V1_STR}/health"
    }
