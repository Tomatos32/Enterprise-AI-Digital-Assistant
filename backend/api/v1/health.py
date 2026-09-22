"""Health Probe Endpoint with Real Physical Service Checks and External Integration Matrix."""

from fastapi import APIRouter
from backend.core.config import settings
from backend.core.redis import check_redis_health
from backend.db.session import check_mysql_health
from backend.rag.vector_store import check_qdrant_health
from backend.adapters.factory import check_all_adapters_health

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Liveness and Readiness probe endpoint inspecting MySQL, Redis, Qdrant connectivity.
    """
    mysql_ok = check_mysql_health()
    redis_ok = await check_redis_health()
    qdrant_ok = check_qdrant_health()

    all_healthy = mysql_ok and redis_ok and qdrant_ok
    status_str = "HEALTHY" if all_healthy else "DEGRADED"

    return {
        "status": status_str,
        "version": settings.VERSION,
        "services": {
            "mysql": "UP" if mysql_ok else "DOWN",
            "redis": "UP" if redis_ok else "DOWN",
            "qdrant": "UP" if qdrant_ok else "DOWN"
        }
    }


@router.get("/health/integrations")
async def health_integrations_check():
    """
    Dynamic Integration Probe inspecting connectivity and latency of external enterprise systems
    (HR OpenAPI, ERP MM/OData, OA/Jira, WeCom Webhook, Dify Workflows).
    """
    result = await check_all_adapters_health()
    return result
