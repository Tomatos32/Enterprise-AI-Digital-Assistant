"""Saga Orchestrator for Distributed Long Transactions and Multi-System Rollback.

Provides Orchestrator-based Saga coordination for enterprise multi-system writes
(ERP inventory, Finance budget, OA tickets), supporting LIFO reverse compensation,
failure isolation, and idempotent rollback.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import inspect
import logging
from typing import Any, Callable, Dict, List, Optional
import uuid

logger = logging.getLogger(__name__)


class SagaStatus(str, Enum):
    """Saga execution status lifecycle."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    COMPENSATING = "COMPENSATING"
    COMPENSATED = "COMPENSATED"
    FAILED = "FAILED"


class SagaExecutionError(Exception):
    """Exception raised when a Saga step fails."""
    def __init__(self, step_name: str, original_error: Exception):
        super().__init__(f"Step '{step_name}' failed: {original_error}")
        self.step_name = step_name
        self.original_error = original_error


class ApprovalRejectedError(Exception):
    """Raised when an approval checkpoint is explicitly rejected."""
    def __init__(self, reason: str = "Human approval rejected"):
        super().__init__(reason)
        self.reason = reason


@dataclass
class ActionStep:
    """Represents an atomic step in a Saga workflow with compensation."""
    name: str
    execute_fn: Callable[..., Any]
    compensate_fn: Callable[..., Any]
    description: str = ""


@dataclass
class StepRecord:
    """Execution record for auditing and compensation."""
    step_name: str
    status: str  # "SUCCESS", "FAILED", "COMPENSATED", "COMPENSATION_FAILED"
    input_context: Dict[str, Any]
    output_result: Optional[Any] = None
    error_message: Optional[str] = None
    executed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    compensated_at: Optional[str] = None


class SagaOrchestrator:
    """Orchestrator-based Saga coordinator with reverse LIFO compensation."""

    def __init__(self, saga_id: Optional[str] = None):
        self.saga_id: str = saga_id or f"saga_{uuid.uuid4().hex[:12]}"
        self.steps: List[ActionStep] = []
        self.status: SagaStatus = SagaStatus.PENDING
        self.execution_stack: List[StepRecord] = []
        self.compensated_stack: List[StepRecord] = []
        self.context: Dict[str, Any] = {}
        self.error: Optional[Exception] = None

    def add_step(
        self,
        name: str,
        execute_fn: Callable[..., Any],
        compensate_fn: Callable[..., Any],
        description: str = "",
    ) -> "SagaOrchestrator":
        """Register a forward step and its corresponding compensation action."""
        step = ActionStep(
            name=name,
            execute_fn=execute_fn,
            compensate_fn=compensate_fn,
            description=description,
        )
        self.steps.append(step)
        return self

    async def _invoke_callable(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Helper to invoke either synchronous or asynchronous callables."""
        if inspect.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        return func(*args, **kwargs)

    async def execute(self, initial_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute all registered steps sequentially.

        If any step fails, automatically trigger LIFO reverse compensation
        for all successfully completed steps.
        """
        self.context = dict(initial_context or {})
        self.status = SagaStatus.RUNNING
        self.execution_stack.clear()
        self.compensated_stack.clear()
        self.error = None

        logger.info("[Saga:%s] Starting execution with %d steps", self.saga_id, len(self.steps))

        for step in self.steps:
            step_record = StepRecord(
                step_name=step.name,
                status="RUNNING",
                input_context=dict(self.context),
            )
            try:
                logger.info("[Saga:%s] Executing step '%s'", self.saga_id, step.name)
                result = await self._invoke_callable(step.execute_fn, self.context)

                # Update context if step returned a dictionary
                if isinstance(result, dict):
                    self.context.update(result)

                step_record.status = "SUCCESS"
                step_record.output_result = result
                self.execution_stack.append(step_record)
                logger.info("[Saga:%s] Step '%s' succeeded", self.saga_id, step.name)

            except Exception as exc:
                step_record.status = "FAILED"
                step_record.error_message = str(exc)
                self.error = exc
                logger.error(
                    "[Saga:%s] Step '%s' encountered failure: %s. Initiating compensation...",
                    self.saga_id,
                    step.name,
                    exc,
                )
                await self._compensate()
                raise SagaExecutionError(step.name, exc) from exc

        self.status = SagaStatus.SUCCESS
        logger.info("[Saga:%s] Completed all steps successfully", self.saga_id)
        return self.context

    async def _compensate(self) -> None:
        """Trigger LIFO reverse compensation for all completed steps."""
        self.status = SagaStatus.COMPENSATING
        logger.warning(
            "[Saga:%s] Compensating %d executed steps in reverse order (LIFO)",
            self.saga_id,
            len(self.execution_stack),
        )

        step_map = {step.name: step for step in self.steps}

        # Pop from top of stack in reverse order
        while self.execution_stack:
            record = self.execution_stack.pop()
            step_def = step_map.get(record.step_name)

            if not step_def:
                logger.error("[Saga:%s] Missing step definition for '%s'", self.saga_id, record.step_name)
                continue

            try:
                logger.info("[Saga:%s] Rolling back step '%s'", self.saga_id, record.step_name)
                # Pass both the context and output result of the step to ensure idempotent compensation
                comp_context = dict(self.context)
                if isinstance(record.output_result, dict):
                    comp_context.update(record.output_result)

                await self._invoke_callable(step_def.compensate_fn, comp_context)
                record.status = "COMPENSATED"
                record.compensated_at = datetime.utcnow().isoformat()
                self.compensated_stack.append(record)
                logger.info("[Saga:%s] Step '%s' rollback succeeded", self.saga_id, record.step_name)

            except Exception as comp_err:
                record.status = "COMPENSATION_FAILED"
                record.error_message = f"Compensation error: {comp_err}"
                self.compensated_stack.append(record)
                self.status = SagaStatus.FAILED
                logger.critical(
                    "[Saga:%s] Critical: Step '%s' compensation failed: %s",
                    self.saga_id,
                    record.step_name,
                    comp_err,
                )
                return

        self.status = SagaStatus.COMPENSATED
        logger.info("[Saga:%s] All steps compensated successfully", self.saga_id)


# =====================================================================
# Enterprise Mock Systems & Idempotent Handlers (ERP, Finance, OA)
# =====================================================================

class EnterpriseSystemState:
    """In-memory state store for ERP, Finance, and OA mock transactions."""

    def __init__(self) -> None:
        # ERP inventory locks: lock_id -> {"item_id": ..., "quantity": ..., "status": "LOCKED" | "UNLOCKED"}
        self.inventory_locks: Dict[str, Dict[str, Any]] = {}
        # Finance budget freezes: freeze_id -> {"department": ..., "amount": ..., "status": "FROZEN" | "REFUNDED"}
        self.budget_freezes: Dict[str, Dict[str, Any]] = {}
        # OA tickets: ticket_id -> {"title": ..., "applicant_id": ..., "status": "CREATED" | "CANCELLED"}
        self.oa_tickets: Dict[str, Dict[str, Any]] = {}
        # Call counters for verifying compensation idempotency
        self.compensation_calls: Dict[str, int] = {
            "erp_unlock": 0,
            "finance_refund": 0,
            "oa_cancel": 0,
        }

    def reset(self) -> None:
        """Reset state for clean unit test runs."""
        self.inventory_locks.clear()
        self.budget_freezes.clear()
        self.oa_tickets.clear()
        for key in self.compensation_calls:
            self.compensation_calls[key] = 0


# Global singleton instance for system operations
mock_enterprise_systems = EnterpriseSystemState()


# --- 1. ERP Inventory Operations ---

def erp_lock_inventory(context: Dict[str, Any]) -> Dict[str, Any]:
    """Forward action: Lock inventory in ERP system."""
    item_id = context.get("item_id", "ITEM_DEFAULT_001")
    quantity = context.get("quantity", 1)

    lock_id = f"LOCK_{uuid.uuid4().hex[:8].upper()}"
    mock_enterprise_systems.inventory_locks[lock_id] = {
        "item_id": item_id,
        "quantity": quantity,
        "status": "LOCKED",
        "created_at": datetime.utcnow().isoformat(),
    }
    logger.info("[ERP] Locked inventory: item=%s, qty=%d, lock_id=%s", item_id, quantity, lock_id)
    return {"erp_lock_id": lock_id, "erp_status": "LOCKED"}


def erp_unlock_inventory(context: Dict[str, Any]) -> Dict[str, Any]:
    """Compensating action: Unlock inventory (Idempotent)."""
    mock_enterprise_systems.compensation_calls["erp_unlock"] += 1
    lock_id = context.get("erp_lock_id")

    if not lock_id or lock_id not in mock_enterprise_systems.inventory_locks:
        logger.warning("[ERP] Unlock requested for non-existent or null lock_id: %s (Idempotent OK)", lock_id)
        return {"erp_status": "NOT_FOUND_OR_SKIPPED"}

    record = mock_enterprise_systems.inventory_locks[lock_id]
    if record["status"] == "UNLOCKED":
        logger.info("[ERP] Lock %s already UNLOCKED. Skipping (Idempotent OK)", lock_id)
        return {"erp_lock_id": lock_id, "erp_status": "UNLOCKED", "already_unlocked": True}

    record["status"] = "UNLOCKED"
    record["unlocked_at"] = datetime.utcnow().isoformat()
    logger.info("[ERP] Successfully unlocked inventory for lock_id=%s", lock_id)
    return {"erp_lock_id": lock_id, "erp_status": "UNLOCKED"}


# --- 2. Finance Budget Operations ---

def finance_deduct_budget(context: Dict[str, Any]) -> Dict[str, Any]:
    """Forward action: Deduct / freeze department budget."""
    department = context.get("department", "R&D")
    amount = float(context.get("amount", 1000.0))

    freeze_id = f"FREEZE_{uuid.uuid4().hex[:8].upper()}"
    mock_enterprise_systems.budget_freezes[freeze_id] = {
        "department": department,
        "amount": amount,
        "status": "FROZEN",
        "created_at": datetime.utcnow().isoformat(),
    }
    logger.info("[Finance] Frozen budget: dept=%s, amount=%.2f, freeze_id=%s", department, amount, freeze_id)
    return {"finance_freeze_id": freeze_id, "finance_status": "FROZEN"}


def finance_refund_budget(context: Dict[str, Any]) -> Dict[str, Any]:
    """Compensating action: Refund frozen department budget (Idempotent)."""
    mock_enterprise_systems.compensation_calls["finance_refund"] += 1
    freeze_id = context.get("finance_freeze_id")

    if not freeze_id or freeze_id not in mock_enterprise_systems.budget_freezes:
        logger.warning("[Finance] Refund requested for unknown freeze_id: %s (Idempotent OK)", freeze_id)
        return {"finance_status": "NOT_FOUND_OR_SKIPPED"}

    record = mock_enterprise_systems.budget_freezes[freeze_id]
    if record["status"] == "REFUNDED":
        logger.info("[Finance] Freeze %s already REFUNDED. Skipping (Idempotent OK)", freeze_id)
        return {"finance_freeze_id": freeze_id, "finance_status": "REFUNDED", "already_refunded": True}

    record["status"] = "REFUNDED"
    record["refunded_at"] = datetime.utcnow().isoformat()
    logger.info("[Finance] Successfully refunded budget for freeze_id=%s", freeze_id)
    return {"finance_freeze_id": freeze_id, "finance_status": "REFUNDED"}


# --- 3. OA Ticket Operations ---

def oa_create_ticket(context: Dict[str, Any]) -> Dict[str, Any]:
    """Forward action: Create procurement approval ticket in OA system."""
    title = context.get("title", "Standard Procurement Ticket")
    applicant_id = context.get("applicant_id", "EMP_001")

    ticket_id = f"TICKET_{uuid.uuid4().hex[:8].upper()}"
    mock_enterprise_systems.oa_tickets[ticket_id] = {
        "title": title,
        "applicant_id": applicant_id,
        "status": "CREATED",
        "created_at": datetime.utcnow().isoformat(),
    }
    logger.info("[OA] Created ticket: title='%s', applicant=%s, ticket_id=%s", title, applicant_id, ticket_id)
    return {"oa_ticket_id": ticket_id, "oa_status": "CREATED"}


def oa_cancel_ticket(context: Dict[str, Any]) -> Dict[str, Any]:
    """Compensating action: Cancel / invalidate OA ticket (Idempotent)."""
    mock_enterprise_systems.compensation_calls["oa_cancel"] += 1
    ticket_id = context.get("oa_ticket_id")

    if not ticket_id or ticket_id not in mock_enterprise_systems.oa_tickets:
        logger.warning("[OA] Cancel requested for unknown ticket_id: %s (Idempotent OK)", ticket_id)
        return {"oa_status": "NOT_FOUND_OR_SKIPPED"}

    record = mock_enterprise_systems.oa_tickets[ticket_id]
    if record["status"] == "CANCELLED":
        logger.info("[OA] Ticket %s already CANCELLED. Skipping (Idempotent OK)", ticket_id)
        return {"oa_ticket_id": ticket_id, "oa_status": "CANCELLED", "already_cancelled": True}

    record["status"] = "CANCELLED"
    record["cancelled_at"] = datetime.utcnow().isoformat()
    logger.info("[OA] Successfully cancelled OA ticket_id=%s", ticket_id)
    return {"oa_ticket_id": ticket_id, "oa_status": "CANCELLED"}
