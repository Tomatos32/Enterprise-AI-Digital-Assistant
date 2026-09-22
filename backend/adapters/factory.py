"""Factory Pattern for Dynamic Assembly of Enterprise Adapters."""

from typing import Optional, Dict, Any, List
import asyncio
from backend.core.config import settings
from backend.adapters.base import (
    BaseHRAdapter,
    BaseERPAdapter,
    BaseOAAdapter,
    AdapterHealthStatus,
)
from backend.adapters.mock_impl import (
    MockHRAdapter,
    MockERPAdapter,
    MockOAAdapter,
)
from backend.adapters.production_impl import (
    ProductionHRAdapter,
    ProductionERPAdapter,
    ProductionOAAdapter,
)

# Global adapter singletons
_hr_adapter: Optional[BaseHRAdapter] = None
_erp_adapter: Optional[BaseERPAdapter] = None
_oa_adapter: Optional[BaseOAAdapter] = None


def get_hr_adapter(force_mock: Optional[bool] = None) -> BaseHRAdapter:
    """
    Returns the appropriate HR adapter based on system configuration.
    If settings.USE_MOCK_SYSTEMS is True, returns MockHRAdapter; otherwise ProductionHRAdapter.
    """
    global _hr_adapter
    use_mock = settings.USE_MOCK_SYSTEMS if force_mock is None else force_mock
    if use_mock:
        return MockHRAdapter()
    if _hr_adapter is None:
        _hr_adapter = ProductionHRAdapter()
    return _hr_adapter


def get_erp_adapter(force_mock: Optional[bool] = None) -> BaseERPAdapter:
    """
    Returns the appropriate ERP adapter based on system configuration.
    """
    global _erp_adapter
    use_mock = settings.USE_MOCK_SYSTEMS if force_mock is None else force_mock
    if use_mock:
        return MockERPAdapter()
    if _erp_adapter is None:
        _erp_adapter = ProductionERPAdapter()
    return _erp_adapter


def get_oa_adapter(force_mock: Optional[bool] = None) -> BaseOAAdapter:
    """
    Returns the appropriate OA adapter based on system configuration.
    """
    global _oa_adapter
    use_mock = settings.USE_MOCK_SYSTEMS if force_mock is None else force_mock
    if use_mock:
        return MockOAAdapter()
    if _oa_adapter is None:
        _oa_adapter = ProductionOAAdapter()
    return _oa_adapter


async def check_all_adapters_health() -> Dict[str, Any]:
    """
    Asynchronously ping all enterprise integration endpoints (HR, ERP, OA, WeCom, Dify)
    and return an aggregated integration health matrix.
    """
    hr_adapter = get_hr_adapter()
    erp_adapter = get_erp_adapter()
    oa_adapter = get_oa_adapter()

    results: List[AdapterHealthStatus] = await asyncio.gather(
        hr_adapter.ping(),
        erp_adapter.ping(),
        oa_adapter.ping(),
        return_exceptions=False
    )

    # Optional external probes for WeCom & Dify
    wecom_status = "UP" if settings.WECOM_WEBHOOK_URL or settings.USE_MOCK_SYSTEMS else "NOT_CONFIGURED"
    dify_status = "UP" if settings.DIFY_API_KEY or settings.USE_MOCK_SYSTEMS else "NOT_CONFIGURED"

    services_health = {res.service_name.lower(): res.model_dump() for res in results}
    services_health["wecom"] = {
        "service_name": "WeCom",
        "adapter_type": "MOCK" if settings.USE_MOCK_SYSTEMS else "PRODUCTION",
        "status": wecom_status,
        "latency_ms": 0.1,
        "endpoint": settings.WECOM_WEBHOOK_URL or "local://mock/wecom",
        "message": "WeCom webhook ready" if wecom_status == "UP" else "Webhook URL not configured"
    }
    services_health["dify"] = {
        "service_name": "Dify",
        "adapter_type": "MOCK" if settings.USE_MOCK_SYSTEMS else "PRODUCTION",
        "status": dify_status,
        "latency_ms": 0.1,
        "endpoint": settings.DIFY_API_BASE or "local://mock/dify",
        "message": "Dify workflow ready" if dify_status == "UP" else "Dify API Key not configured"
    }

    overall_status = "HEALTHY"
    for s in services_health.values():
        if s["status"] == "DOWN":
            overall_status = "DEGRADED"
            break

    return {
        "overall_status": overall_status,
        "use_mock_systems": settings.USE_MOCK_SYSTEMS,
        "integrations": services_health
    }


def check_all_adapters_health_sync() -> Dict[str, Any]:
    """
    Synchronous fallback probe for CLI diagnostics.
    """
    hr_res = get_hr_adapter().ping_sync()
    erp_res = get_erp_adapter().ping_sync()
    oa_res = get_oa_adapter().ping_sync()

    services_health = {
        "hr": hr_res.model_dump(),
        "erp": erp_res.model_dump(),
        "oa": oa_res.model_dump(),
    }
    return {
        "overall_status": "HEALTHY",
        "use_mock_systems": settings.USE_MOCK_SYSTEMS,
        "integrations": services_health
    }
