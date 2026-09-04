"""Unit tests for Distributed Saga Orchestrator and Multi-System Rollback.

Verifies:
1. Full forward execution success.
2. Step-3 network timeout triggering LIFO reverse compensation.
3. Idempotency of compensating actions.
4. Human approval rejection rollback.
"""

import pytest

from backend.core.saga_orchestrator import (
    ApprovalRejectedError,
    SagaExecutionError,
    SagaOrchestrator,
    SagaStatus,
    erp_lock_inventory,
    erp_unlock_inventory,
    finance_deduct_budget,
    finance_refund_budget,
    mock_enterprise_systems,
    oa_cancel_ticket,
    oa_create_ticket,
)


@pytest.fixture(autouse=True)
def reset_mock_systems():
    """Reset mock enterprise systems state before each test."""
    mock_enterprise_systems.reset()
    yield
    mock_enterprise_systems.reset()


@pytest.mark.asyncio
async def test_saga_full_forward_success():
    """Verify standard happy-path forward execution across ERP, Finance, and OA."""
    saga = SagaOrchestrator(saga_id="test_saga_success")
    saga.add_step("erp_lock", erp_lock_inventory, erp_unlock_inventory)
    saga.add_step("finance_deduct", finance_deduct_budget, finance_refund_budget)
    saga.add_step("oa_ticket", oa_create_ticket, oa_cancel_ticket)

    initial_context = {
        "item_id": "ITEM_MACBOOK_M3",
        "quantity": 2,
        "department": "Engineering",
        "amount": 32000.0,
        "title": "MacBook Pro M3 Procurement",
        "applicant_id": "EMP_DEV_007",
    }

    result = await saga.execute(initial_context)

    # Verify Saga state
    assert saga.status == SagaStatus.SUCCESS
    assert len(saga.execution_stack) == 3
    assert len(saga.compensated_stack) == 0

    # Verify context outputs
    assert "erp_lock_id" in result
    assert result["erp_status"] == "LOCKED"
    assert "finance_freeze_id" in result
    assert result["finance_status"] == "FROZEN"
    assert "oa_ticket_id" in result
    assert result["oa_status"] == "CREATED"

    # Verify underlying system states
    lock_record = mock_enterprise_systems.inventory_locks[result["erp_lock_id"]]
    assert lock_record["status"] == "LOCKED"
    assert lock_record["quantity"] == 2

    freeze_record = mock_enterprise_systems.budget_freezes[result["finance_freeze_id"]]
    assert freeze_record["status"] == "FROZEN"
    assert freeze_record["amount"] == 32000.0

    ticket_record = mock_enterprise_systems.oa_tickets[result["oa_ticket_id"]]
    assert ticket_record["status"] == "CREATED"

    # Compensation counters must be 0
    assert mock_enterprise_systems.compensation_calls["erp_unlock"] == 0
    assert mock_enterprise_systems.compensation_calls["finance_refund"] == 0
    assert mock_enterprise_systems.compensation_calls["oa_cancel"] == 0


@pytest.mark.asyncio
async def test_saga_step3_timeout_reverse_rollback():
    """Verify that a network timeout at Step 3 triggers LIFO reverse compensation for Steps 1 & 2."""
    saga = SagaOrchestrator(saga_id="test_saga_timeout")

    rollback_order = []

    # Wrapper to observe reverse rollback execution order
    def tracked_finance_refund(context):
        rollback_order.append("finance_refund")
        return finance_refund_budget(context)

    def tracked_erp_unlock(context):
        rollback_order.append("erp_unlock")
        return erp_unlock_inventory(context)

    # Step 3 simulates network timeout
    def failing_oa_step(context):
        raise TimeoutError("Connection to OA Gateway timed out after 5000ms")

    saga.add_step("erp_lock", erp_lock_inventory, tracked_erp_unlock)
    saga.add_step("finance_deduct", finance_deduct_budget, tracked_finance_refund)
    saga.add_step("oa_ticket", failing_oa_step, oa_cancel_ticket)

    initial_context = {
        "item_id": "SERVER_BLADE_01",
        "quantity": 5,
        "department": "IT_OPS",
        "amount": 75000.0,
        "title": "Data Center Expansion",
    }

    with pytest.raises(SagaExecutionError) as exc_info:
        await saga.execute(initial_context)

    assert "oa_ticket" in str(exc_info.value)
    assert isinstance(exc_info.value.original_error, TimeoutError)

    # Verify Saga status switched to COMPENSATED
    assert saga.status == SagaStatus.COMPENSATED

    # Verify LIFO reverse execution order: Finance was Step 2, ERP was Step 1
    # Rollback must execute Step 2 (Finance) first, then Step 1 (ERP)
    assert rollback_order == ["finance_refund", "erp_unlock"]

    # Verify system state was completely rolled back
    lock_id = saga.context.get("erp_lock_id")
    assert lock_id is not None
    assert mock_enterprise_systems.inventory_locks[lock_id]["status"] == "UNLOCKED"

    freeze_id = saga.context.get("finance_freeze_id")
    assert freeze_id is not None
    assert mock_enterprise_systems.budget_freezes[freeze_id]["status"] == "REFUNDED"

    # OA ticket was never created
    assert len(mock_enterprise_systems.oa_tickets) == 0


@pytest.mark.asyncio
async def test_compensation_idempotency():
    """Verify that executing compensating actions multiple times is 100% idempotent."""
    context = {
        "item_id": "ITEM_OFFICE_CHAIR",
        "quantity": 10,
        "department": "Admin",
        "amount": 5000.0,
        "title": "Office Ergonomics",
    }

    # 1. Forward actions
    erp_res = erp_lock_inventory(context)
    fin_res = finance_deduct_budget(context)
    oa_res = oa_create_ticket(context)

    merged_ctx = {**context, **erp_res, **fin_res, **oa_res}

    # 2. First compensation pass
    unlock_1 = erp_unlock_inventory(merged_ctx)
    refund_1 = finance_refund_budget(merged_ctx)
    cancel_1 = oa_cancel_ticket(merged_ctx)

    assert unlock_1["erp_status"] == "UNLOCKED"
    assert refund_1["finance_status"] == "REFUNDED"
    assert cancel_1["oa_status"] == "CANCELLED"

    # 3. Second compensation pass (Idempotency test)
    unlock_2 = erp_unlock_inventory(merged_ctx)
    refund_2 = finance_refund_budget(merged_ctx)
    cancel_2 = oa_cancel_ticket(merged_ctx)

    assert unlock_2["erp_status"] == "UNLOCKED"
    assert unlock_2.get("already_unlocked") is True
    assert refund_2["finance_status"] == "REFUNDED"
    assert refund_2.get("already_refunded") is True
    assert cancel_2["oa_status"] == "CANCELLED"
    assert cancel_2.get("already_cancelled") is True

    # Check that system states remain consistent
    assert mock_enterprise_systems.inventory_locks[erp_res["erp_lock_id"]]["status"] == "UNLOCKED"
    assert mock_enterprise_systems.budget_freezes[fin_res["finance_freeze_id"]]["status"] == "REFUNDED"
    assert mock_enterprise_systems.oa_tickets[oa_res["oa_ticket_id"]]["status"] == "CANCELLED"

    assert mock_enterprise_systems.compensation_calls["erp_unlock"] == 2
    assert mock_enterprise_systems.compensation_calls["finance_refund"] == 2
    assert mock_enterprise_systems.compensation_calls["oa_cancel"] == 2


@pytest.mark.asyncio
async def test_saga_human_approval_rejection_rollback():
    """Verify rollback when human-in-the-loop approval rejects the transaction."""
    saga = SagaOrchestrator(saga_id="test_saga_approval_rejection")

    def mock_human_approval_step(context):
        # Simulate manager rejecting excessive procurement
        raise ApprovalRejectedError("Department budget quota exceeded for Q3")

    saga.add_step("erp_lock", erp_lock_inventory, erp_unlock_inventory)
    saga.add_step("finance_deduct", finance_deduct_budget, finance_refund_budget)
    saga.add_step("approval_check", mock_human_approval_step, lambda ctx: None)

    initial_context = {
        "item_id": "EXPENSIVE_GPU_CLUSTER",
        "quantity": 1,
        "department": "AI_RESEARCH",
        "amount": 250000.0,
    }

    with pytest.raises(SagaExecutionError) as exc_info:
        await saga.execute(initial_context)

    assert isinstance(exc_info.value.original_error, ApprovalRejectedError)
    assert saga.status == SagaStatus.COMPENSATED

    # Verify ERP and Finance were properly compensated
    lock_id = saga.context.get("erp_lock_id")
    freeze_id = saga.context.get("finance_freeze_id")

    assert mock_enterprise_systems.inventory_locks[lock_id]["status"] == "UNLOCKED"
    assert mock_enterprise_systems.budget_freezes[freeze_id]["status"] == "REFUNDED"
