"""Base Abstract Classes and Contracts for Enterprise System Adapters."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class AdapterHealthStatus(BaseModel):
    """Health probe result for an external enterprise system adapter."""
    service_name: str = Field(..., description="Service identifier (e.g. HR, ERP, OA)")
    adapter_type: str = Field(..., description="'MOCK' or 'PRODUCTION'")
    status: str = Field(..., description="'UP', 'DOWN', or 'DEGRADED'")
    latency_ms: float = Field(default=0.0, description="Response time in milliseconds")
    endpoint: Optional[str] = Field(default=None, description="Remote API endpoint checked")
    message: str = Field(default="OK", description="Detailed status message")


class BaseHRAdapter(ABC):
    """Abstract Interface for Human Resources (HR) Enterprise System Adapter."""

    @abstractmethod
    def get_employee(self, id_or_name: str, department: Optional[str] = None) -> Dict[str, Any]:
        """Query employee details by ID or Name."""
        pass

    @abstractmethod
    def list_employees(self, department: Optional[str] = None) -> Dict[str, Any]:
        """List all employees or filter by department."""
        pass

    @abstractmethod
    async def ping(self) -> AdapterHealthStatus:
        """Asynchronously probe external HR endpoint connectivity and token validity."""
        pass

    @abstractmethod
    def ping_sync(self) -> AdapterHealthStatus:
        """Synchronously probe connectivity for CLI or synchronous health checks."""
        pass


class BaseERPAdapter(ABC):
    """Abstract Interface for Enterprise Resource Planning (ERP) System Adapter."""

    @abstractmethod
    def get_inventory(self, item_name: Optional[str] = None, category: Optional[str] = None) -> Dict[str, Any]:
        """Query equipment inventory stock by name or category."""
        pass

    @abstractmethod
    def create_purchase(
        self,
        item_name: str,
        quantity: int,
        unit_price: float,
        department: str,
        reason: str = "办公采购"
    ) -> Dict[str, Any]:
        """Create a new procurement purchase order in ERP."""
        pass

    @abstractmethod
    async def ping(self) -> AdapterHealthStatus:
        """Asynchronously probe external ERP endpoint connectivity."""
        pass

    @abstractmethod
    def ping_sync(self) -> AdapterHealthStatus:
        """Synchronously probe external ERP endpoint connectivity."""
        pass


class BaseOAAdapter(ABC):
    """Abstract Interface for Office Automation (OA) & Ticketing System Adapter."""

    @abstractmethod
    def create_ticket(
        self,
        title: str,
        description: str,
        priority: str = "P3",
        department: str = "IT"
    ) -> Dict[str, Any]:
        """Submit a service or IT support ticket in OA system."""
        pass

    @abstractmethod
    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str
    ) -> Dict[str, Any]:
        """Send notification email via OA system."""
        pass

    @abstractmethod
    async def ping(self) -> AdapterHealthStatus:
        """Asynchronously probe external OA endpoint connectivity."""
        pass

    @abstractmethod
    def ping_sync(self) -> AdapterHealthStatus:
        """Synchronously probe external OA endpoint connectivity."""
        pass
