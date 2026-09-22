"""Production Implementation for Enterprise System Adapters with HTTP Connection Pooling and Retries."""

import time
import logging
from typing import Optional, Dict, Any
import httpx

from backend.adapters.base import (
    BaseHRAdapter,
    BaseERPAdapter,
    BaseOAAdapter,
    AdapterHealthStatus,
)
from backend.core.config import settings
from backend.core.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


class ProductionHRAdapter(BaseHRAdapter):
    """
    Production HR Adapter connecting to external OpenAPI (e.g., Feishu Contact / Beisen / SAP SuccessFactors).
    Features HTTP connection pooling, Bearer Token authentication, and retry with exponential backoff.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_token: Optional[str] = None,
        timeout: float = 5.0,
        max_retries: int = 3,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ):
        self.base_url = (base_url or settings.HR_BASE_URL or "https://open.feishu.cn").rstrip("/")
        self.api_token = api_token or settings.HR_API_TOKEN or "default_prod_hr_token"
        self.timeout = timeout
        self.max_retries = max_retries
        self.circuit_breaker = circuit_breaker
        self._limits = httpx.Limits(max_keepalive_connections=20, max_connections=100)

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "User-Agent": "Enterprise-AI-Digital-Assistant/1.0"
        }

    def _request_with_retry(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        if self.circuit_breaker and not self.circuit_breaker.can_execute():
            logger.warning(f"[ProductionHRAdapter] CircuitBreaker is OPEN for {url}, fast failing.")
            return {
                "status": "CIRCUIT_OPEN",
                "code": 503,
                "message": f"Circuit breaker [{self.circuit_breaker.name}] is OPEN. Fast failing request.",
                "data": []
            }

        last_exception = None

        for attempt in range(self.max_retries):
            try:
                with httpx.Client(limits=self._limits, timeout=self.timeout) as client:
                    resp = client.request(
                        method=method,
                        url=url,
                        headers=self._get_headers(),
                        params=params,
                        json=json_data
                    )
                    resp.raise_for_status()
                    if self.circuit_breaker:
                        self.circuit_breaker.record_success()
                    return resp.json()
            except (httpx.TimeoutException, httpx.RequestError) as exc:
                last_exception = exc
                logger.warning(
                    f"[ProductionHRAdapter] Request failed (attempt {attempt + 1}/{self.max_retries}) for {url}: {exc}"
                )
                time.sleep(0.05 * (2 ** attempt))
            except Exception as exc:
                logger.error(f"[ProductionHRAdapter] Unrecoverable error calling {url}: {exc}")
                if self.circuit_breaker:
                    self.circuit_breaker.record_failure(exc)
                return {
                    "status": "ERROR",
                    "code": 500,
                    "message": f"HR 系统远端异常: {str(exc)}",
                    "data": []
                }

        # Graceful degradation fallback
        logger.error(f"[ProductionHRAdapter] Max retries reached for {url}: {last_exception}")
        if self.circuit_breaker:
            self.circuit_breaker.record_failure(last_exception)
        return {
            "status": "DEGRADED",
            "code": 504,
            "message": f"HR 外部系统通信超时，已触发降级保护: {str(last_exception)}",
            "data": []
        }

    def get_employee(self, id_or_name: str, department: Optional[str] = None) -> Dict[str, Any]:
        params = {"query": id_or_name}
        if department:
            params["department"] = department
        return self._request_with_retry("GET", f"/open-apis/contact/v3/users/{id_or_name}", params=params)

    def list_employees(self, department: Optional[str] = None) -> Dict[str, Any]:
        params = {"department": department} if department else {}
        return self._request_with_retry("GET", "/open-apis/contact/v3/users", params=params)

    async def ping(self) -> AdapterHealthStatus:
        start_time = time.perf_counter()
        endpoint = f"{self.base_url}/health"
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(endpoint, headers=self._get_headers())
                latency = round((time.perf_counter() - start_time) * 1000, 2)
                is_up = resp.status_code < 500
                return AdapterHealthStatus(
                    service_name="HR",
                    adapter_type="PRODUCTION",
                    status="UP" if is_up else "DOWN",
                    latency_ms=latency,
                    endpoint=endpoint,
                    message=f"HTTP {resp.status_code}"
                )
        except Exception as exc:
            latency = round((time.perf_counter() - start_time) * 1000, 2)
            return AdapterHealthStatus(
                service_name="HR",
                adapter_type="PRODUCTION",
                status="DOWN",
                latency_ms=latency,
                endpoint=endpoint,
                message=f"Connection failure: {str(exc)}"
            )

    def ping_sync(self) -> AdapterHealthStatus:
        start_time = time.perf_counter()
        endpoint = f"{self.base_url}/health"
        try:
            with httpx.Client(timeout=2.0) as client:
                resp = client.get(endpoint, headers=self._get_headers())
                latency = round((time.perf_counter() - start_time) * 1000, 2)
                is_up = resp.status_code < 500
                return AdapterHealthStatus(
                    service_name="HR",
                    adapter_type="PRODUCTION",
                    status="UP" if is_up else "DOWN",
                    latency_ms=latency,
                    endpoint=endpoint,
                    message=f"HTTP {resp.status_code}"
                )
        except Exception as exc:
            latency = round((time.perf_counter() - start_time) * 1000, 2)
            return AdapterHealthStatus(
                service_name="HR",
                adapter_type="PRODUCTION",
                status="DOWN",
                latency_ms=latency,
                endpoint=endpoint,
                message=f"Connection failure: {str(exc)}"
            )


class ProductionERPAdapter(BaseERPAdapter):
    """
    Production ERP Adapter connecting to SAP MM / Yonyou NC Cloud / Kingdee Cloud REST APIs.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_token: Optional[str] = None,
        timeout: float = 5.0,
        max_retries: int = 3,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ):
        self.base_url = (base_url or settings.ERP_BASE_URL or "https://erp.internal.corp").rstrip("/")
        self.api_token = api_token or settings.ERP_API_TOKEN or "default_prod_erp_token"
        self.timeout = timeout
        self.max_retries = max_retries
        self.circuit_breaker = circuit_breaker
        self._limits = httpx.Limits(max_keepalive_connections=20, max_connections=100)

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "X-ERP-Client": "Enterprise-AI-Agent"
        }

    def _request_with_retry(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        if self.circuit_breaker and not self.circuit_breaker.can_execute():
            logger.warning(f"[ProductionERPAdapter] CircuitBreaker is OPEN for {url}, fast failing.")
            return {
                "status": "CIRCUIT_OPEN",
                "code": 503,
                "message": f"Circuit breaker [{self.circuit_breaker.name}] is OPEN. Fast failing request."
            }

        last_exception = None

        for attempt in range(self.max_retries):
            try:
                with httpx.Client(limits=self._limits, timeout=self.timeout) as client:
                    resp = client.request(
                        method=method,
                        url=url,
                        headers=self._get_headers(),
                        params=params,
                        json=json_data
                    )
                    resp.raise_for_status()
                    if self.circuit_breaker:
                        self.circuit_breaker.record_success()
                    return resp.json()
            except (httpx.TimeoutException, httpx.RequestError) as exc:
                last_exception = exc
                logger.warning(
                    f"[ProductionERPAdapter] Request failed (attempt {attempt + 1}/{self.max_retries}) for {url}: {exc}"
                )
                time.sleep(0.05 * (2 ** attempt))
            except Exception as exc:
                logger.error(f"[ProductionERPAdapter] Error calling {url}: {exc}")
                if self.circuit_breaker:
                    self.circuit_breaker.record_failure(exc)
                return {
                    "status": "ERROR",
                    "code": 500,
                    "message": f"ERP 远端异常: {str(exc)}"
                }

        logger.error(f"[ProductionERPAdapter] Max retries reached for {url}: {last_exception}")
        if self.circuit_breaker:
            self.circuit_breaker.record_failure(last_exception)
        return {
            "status": "DEGRADED",
            "code": 504,
            "message": f"ERP 外部系统通信超时，已触发降级保护: {str(last_exception)}"
        }

    def get_inventory(self, item_name: Optional[str] = None, category: Optional[str] = None) -> Dict[str, Any]:
        params = {}
        if item_name:
            params["item_name"] = item_name
        if category:
            params["category"] = category
        return self._request_with_retry("GET", "/api/v2/materials/stock", params=params)

    def create_purchase(
        self,
        item_name: str,
        quantity: int,
        unit_price: float,
        department: str,
        reason: str = "办公采购"
    ) -> Dict[str, Any]:
        payload = {
            "item_name": item_name,
            "quantity": quantity,
            "unit_price": unit_price,
            "total_price": round(quantity * unit_price, 2),
            "department": department,
            "reason": reason
        }
        return self._request_with_retry("POST", "/api/v2/procurement/purchase-orders", json_data=payload)

    async def ping(self) -> AdapterHealthStatus:
        start_time = time.perf_counter()
        endpoint = f"{self.base_url}/health"
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(endpoint, headers=self._get_headers())
                latency = round((time.perf_counter() - start_time) * 1000, 2)
                is_up = resp.status_code < 500
                return AdapterHealthStatus(
                    service_name="ERP",
                    adapter_type="PRODUCTION",
                    status="UP" if is_up else "DOWN",
                    latency_ms=latency,
                    endpoint=endpoint,
                    message=f"HTTP {resp.status_code}"
                )
        except Exception as exc:
            latency = round((time.perf_counter() - start_time) * 1000, 2)
            return AdapterHealthStatus(
                service_name="ERP",
                adapter_type="PRODUCTION",
                status="DOWN",
                latency_ms=latency,
                endpoint=endpoint,
                message=f"Connection failure: {str(exc)}"
            )

    def ping_sync(self) -> AdapterHealthStatus:
        start_time = time.perf_counter()
        endpoint = f"{self.base_url}/health"
        try:
            with httpx.Client(timeout=2.0) as client:
                resp = client.get(endpoint, headers=self._get_headers())
                latency = round((time.perf_counter() - start_time) * 1000, 2)
                is_up = resp.status_code < 500
                return AdapterHealthStatus(
                    service_name="ERP",
                    adapter_type="PRODUCTION",
                    status="UP" if is_up else "DOWN",
                    latency_ms=latency,
                    endpoint=endpoint,
                    message=f"HTTP {resp.status_code}"
                )
        except Exception as exc:
            latency = round((time.perf_counter() - start_time) * 1000, 2)
            return AdapterHealthStatus(
                service_name="ERP",
                adapter_type="PRODUCTION",
                status="DOWN",
                latency_ms=latency,
                endpoint=endpoint,
                message=f"Connection failure: {str(exc)}"
            )


class ProductionOAAdapter(BaseOAAdapter):
    """
    Production OA Adapter connecting to Jira Service Desk / Weaver e-cology REST APIs.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_token: Optional[str] = None,
        timeout: float = 5.0,
        max_retries: int = 3,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ):
        self.base_url = (base_url or settings.OA_BASE_URL or "https://oa.internal.corp").rstrip("/")
        self.api_token = api_token or settings.OA_API_TOKEN or "default_prod_oa_token"
        self.timeout = timeout
        self.max_retries = max_retries
        self.circuit_breaker = circuit_breaker
        self._limits = httpx.Limits(max_keepalive_connections=20, max_connections=100)

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

    def _request_with_retry(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        if self.circuit_breaker and not self.circuit_breaker.can_execute():
            logger.warning(f"[ProductionOAAdapter] CircuitBreaker is OPEN for {url}, fast failing.")
            return {
                "status": "CIRCUIT_OPEN",
                "code": 503,
                "message": f"Circuit breaker [{self.circuit_breaker.name}] is OPEN. Fast failing request."
            }

        last_exception = None

        for attempt in range(self.max_retries):
            try:
                with httpx.Client(limits=self._limits, timeout=self.timeout) as client:
                    resp = client.request(
                        method=method,
                        url=url,
                        headers=self._get_headers(),
                        params=params,
                        json=json_data
                    )
                    resp.raise_for_status()
                    if self.circuit_breaker:
                        self.circuit_breaker.record_success()
                    return resp.json()
            except (httpx.TimeoutException, httpx.RequestError) as exc:
                last_exception = exc
                logger.warning(
                    f"[ProductionOAAdapter] Request failed (attempt {attempt + 1}/{self.max_retries}) for {url}: {exc}"
                )
                time.sleep(0.05 * (2 ** attempt))
            except Exception as exc:
                logger.error(f"[ProductionOAAdapter] Error calling {url}: {exc}")
                if self.circuit_breaker:
                    self.circuit_breaker.record_failure(exc)
                return {
                    "status": "ERROR",
                    "code": 500,
                    "message": f"OA 远端异常: {str(exc)}"
                }

        logger.error(f"[ProductionOAAdapter] Max retries reached for {url}: {last_exception}")
        if self.circuit_breaker:
            self.circuit_breaker.record_failure(last_exception)
        return {
            "status": "DEGRADED",
            "code": 504,
            "message": f"OA 外部系统通信超时，已触发降级保护: {str(last_exception)}"
        }

    def create_ticket(
        self,
        title: str,
        description: str,
        priority: str = "P3",
        department: str = "IT"
    ) -> Dict[str, Any]:
        payload = {
            "title": title,
            "description": description,
            "priority": priority.upper(),
            "department": department.upper()
        }
        return self._request_with_retry("POST", "/rest/api/3/issue", json_data=payload)

    def send_email(self, to_email: str, subject: str, body: str) -> Dict[str, Any]:
        payload = {
            "to": to_email,
            "subject": subject,
            "body": body
        }
        return self._request_with_retry("POST", "/api/v1/mail/send", json_data=payload)

    async def ping(self) -> AdapterHealthStatus:
        start_time = time.perf_counter()
        endpoint = f"{self.base_url}/health"
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(endpoint, headers=self._get_headers())
                latency = round((time.perf_counter() - start_time) * 1000, 2)
                is_up = resp.status_code < 500
                return AdapterHealthStatus(
                    service_name="OA",
                    adapter_type="PRODUCTION",
                    status="UP" if is_up else "DOWN",
                    latency_ms=latency,
                    endpoint=endpoint,
                    message=f"HTTP {resp.status_code}"
                )
        except Exception as exc:
            latency = round((time.perf_counter() - start_time) * 1000, 2)
            return AdapterHealthStatus(
                service_name="OA",
                adapter_type="PRODUCTION",
                status="DOWN",
                latency_ms=latency,
                endpoint=endpoint,
                message=f"Connection failure: {str(exc)}"
            )

    def ping_sync(self) -> AdapterHealthStatus:
        start_time = time.perf_counter()
        endpoint = f"{self.base_url}/health"
        try:
            with httpx.Client(timeout=2.0) as client:
                resp = client.get(endpoint, headers=self._get_headers())
                latency = round((time.perf_counter() - start_time) * 1000, 2)
                is_up = resp.status_code < 500
                return AdapterHealthStatus(
                    service_name="OA",
                    adapter_type="PRODUCTION",
                    status="UP" if is_up else "DOWN",
                    latency_ms=latency,
                    endpoint=endpoint,
                    message=f"HTTP {resp.status_code}"
                )
        except Exception as exc:
            latency = round((time.perf_counter() - start_time) * 1000, 2)
            return AdapterHealthStatus(
                service_name="OA",
                adapter_type="PRODUCTION",
                status="DOWN",
                latency_ms=latency,
                endpoint=endpoint,
                message=f"Connection failure: {str(exc)}"
            )
