"""Enterprise Systems Adapters Architecture Module."""

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

__all__ = [
    "BaseHRAdapter",
    "BaseERPAdapter",
    "BaseOAAdapter",
    "AdapterHealthStatus",
    "MockHRAdapter",
    "MockERPAdapter",
    "MockOAAdapter",
    "ProductionHRAdapter",
    "ProductionERPAdapter",
    "ProductionOAAdapter",
    "get_hr_adapter",
    "get_erp_adapter",
    "get_oa_adapter",
    "check_all_adapters_health",
]
