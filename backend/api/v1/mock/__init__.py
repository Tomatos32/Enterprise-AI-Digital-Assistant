"""Mock APIs Package Initialization."""

from backend.api.v1.mock.hr_mock import router as hr_router
from backend.api.v1.mock.erp_mock import router as erp_router
from backend.api.v1.mock.oa_mock import router as oa_router

__all__ = [
    "hr_router",
    "erp_router",
    "oa_router",
]
