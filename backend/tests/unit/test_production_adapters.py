"""Unit and Integration Tests for Enterprise System Adapters and Dynamic Integration Health Probe."""

import pytest
from unittest.mock import patch, MagicMock
import httpx

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
from backend.adapters.factory import (
    get_hr_adapter,
    get_erp_adapter,
    get_oa_adapter,
    check_all_adapters_health,
)
from backend.tools.impl.employee_tools import query_employee
from backend.tools.impl.inventory_tools import query_inventory
from backend.tools.impl.ticket_tools import create_ticket
from backend.tools.impl.purchase_tools import create_purchase


def test_adapter_factory_mock_assembly():
    """Verify factory returns Mock implementations when USE_MOCK_SYSTEMS=True."""
    with patch.object(settings, "USE_MOCK_SYSTEMS", True):
        hr = get_hr_adapter(force_mock=True)
        erp = get_erp_adapter(force_mock=True)
        oa = get_oa_adapter(force_mock=True)

        assert isinstance(hr, MockHRAdapter)
        assert isinstance(hr, BaseHRAdapter)
        assert isinstance(erp, MockERPAdapter)
        assert isinstance(erp, BaseERPAdapter)
        assert isinstance(oa, MockOAAdapter)
        assert isinstance(oa, BaseOAAdapter)


def test_adapter_factory_production_assembly():
    """Verify factory returns Production implementations when USE_MOCK_SYSTEMS=False."""
    with patch.object(settings, "USE_MOCK_SYSTEMS", False):
        hr = get_hr_adapter(force_mock=False)
        erp = get_erp_adapter(force_mock=False)
        oa = get_oa_adapter(force_mock=False)

        assert isinstance(hr, ProductionHRAdapter)
        assert isinstance(erp, ProductionERPAdapter)
        assert isinstance(oa, ProductionOAAdapter)


def test_tools_seamless_delegation_mock():
    """Verify employee, inventory, ticket and purchase tools delegate seamlessly to Mock adapters."""
    with patch.object(settings, "USE_MOCK_SYSTEMS", True):
        # 1. Employee query tool
        emp_res = query_employee(name="张伟")
        assert emp_res["status"] in ["SUCCESS", "NOT_FOUND"]
        if emp_res["status"] == "SUCCESS":
            assert len(emp_res["data"]) >= 1

        # 2. Inventory query tool
        inv_res = query_inventory(item_name="MacBook")
        assert inv_res["status"] in ["SUCCESS", "NOT_FOUND"]

        # 3. Ticket creation tool
        tck_res = create_ticket(title="网络异常测试", description="WiFi无法连接", priority="P2")
        assert tck_res["status"] == "SUCCESS"
        assert tck_res["priority"] == "P2"
        assert "ticket_id" in tck_res

        # 4. Purchase tool
        po_res = create_purchase(item_name="Dell显示器", quantity=2, unit_price=2000.0, department="研发部")
        assert po_res["status"] == "SUCCESS"
        assert po_res["total_price"] == 4000.0
        assert po_res["approval_status"] == "AUTO_APPROVED"


def test_production_hr_adapter_mocked_http_success():
    """Verify ProductionHRAdapter sends proper Bearer token headers and handles JSON response."""
    adapter = ProductionHRAdapter(
        base_url="https://feishu.mock.internal",
        api_token="test_token_hr_123",
        max_retries=2
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "code": 0,
        "msg": "success",
        "data": {"user_id": "emp_999", "name": "王五", "department": "安全合规部"}
    }
    mock_response.raise_for_status.return_value = None

    with patch("httpx.Client.request", return_value=mock_response) as mock_req:
        res = adapter.get_employee("emp_999")
        assert res["code"] == 0
        assert res["data"]["name"] == "王五"
        mock_req.assert_called_once()
        args, kwargs = mock_req.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer test_token_hr_123"


def test_production_adapters_retry_and_graceful_degradation():
    """Verify Production adapters retry on timeout and return DEGRADED status upon exhaustion."""
    hr_adapter = ProductionHRAdapter(
        base_url="https://timeout.internal",
        api_token="test_token",
        timeout=0.01,
        max_retries=2
    )

    with patch("httpx.Client.request", side_effect=httpx.TimeoutException("Read timed out")) as mock_req:
        res = hr_adapter.get_employee("emp_test")
        assert res["status"] == "DEGRADED"
        assert res["code"] == 504
        assert "通信超时" in res["message"]
        assert mock_req.call_count == 2

    erp_adapter = ProductionERPAdapter(
        base_url="https://timeout.internal",
        timeout=0.01,
        max_retries=2
    )

    with patch("httpx.Client.request", side_effect=httpx.ConnectError("Connection refused")):
        res = erp_adapter.get_inventory("test_item")
        assert res["status"] == "DEGRADED"
        assert res["code"] == 504

    oa_adapter = ProductionOAAdapter(
        base_url="https://timeout.internal",
        timeout=0.01,
        max_retries=2
    )

    with patch("httpx.Client.request", side_effect=httpx.TimeoutException("OA timeout")):
        res = oa_adapter.create_ticket("Title", "Desc")
        assert res["status"] == "DEGRADED"
        assert res["code"] == 504


@pytest.mark.asyncio
async def test_check_all_adapters_health_integration_probe():
    """Verify check_all_adapters_health collects matrix status for all enterprise integrations."""
    matrix = await check_all_adapters_health()

    assert "overall_status" in matrix
    assert matrix["overall_status"] in ["HEALTHY", "DEGRADED"]
    assert "integrations" in matrix

    integrations = matrix["integrations"]
    assert "hr" in integrations
    assert "erp" in integrations
    assert "oa" in integrations
    assert "wecom" in integrations
    assert "dify" in integrations

    assert integrations["hr"]["status"] in ["UP", "DOWN", "DEGRADED"]
    assert integrations["erp"]["status"] in ["UP", "DOWN", "DEGRADED"]
    assert integrations["oa"]["status"] in ["UP", "DOWN", "DEGRADED"]


def test_ping_sync_contracts():
    """Verify synchronous ping contract on mock adapters returns valid Pydantic model."""
    mock_hr = MockHRAdapter()
    status = mock_hr.ping_sync()
    assert isinstance(status, AdapterHealthStatus)
    assert status.service_name == "HR"
    assert status.status == "UP"
    assert status.adapter_type == "MOCK"
