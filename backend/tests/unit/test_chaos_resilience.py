"""Chaos Engineering & Fault Injection Tests: Circuit Breaker, Exponential Backoff, and Saga Resilience."""

import time
import pytest
from unittest.mock import MagicMock

from backend.core.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitBreakerOpenException,
    retry_with_backoff,
)
from backend.adapters.production_impl import ProductionERPAdapter
from backend.core.saga_orchestrator import SagaOrchestrator, SagaStatus, SagaExecutionError


class TestCircuitBreakerStateMachine:
    """Test suite for 3-state Circuit Breaker state transitions."""

    def test_initial_state_is_closed(self):
        cb = CircuitBreaker(name="test_service", failure_threshold=3, recovery_timeout=1.0)
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute() is True

    def test_trip_to_open_on_exceeding_failure_threshold(self):
        cb = CircuitBreaker(
            name="test_service",
            failure_threshold=3,
            failure_rate_threshold=0.5,
            recovery_timeout=1.0,
        )

        def faulty_function():
            raise ConnectionError("Remote ERP unreachable")

        # 1st call fails
        with pytest.raises(ConnectionError):
            cb.call(faulty_function)
        assert cb.state == CircuitState.CLOSED

        # 2nd call fails
        with pytest.raises(ConnectionError):
            cb.call(faulty_function)
        assert cb.state == CircuitState.CLOSED

        # 3rd call fails -> Trips circuit breaker to OPEN
        with pytest.raises(ConnectionError):
            cb.call(faulty_function)
        assert cb.state == CircuitState.OPEN
        assert cb.can_execute() is False

        # 4th call: Fast-fails immediately without calling downstream
        mock_downstream = MagicMock()
        with pytest.raises(CircuitBreakerOpenException) as exc_info:
            cb.call(mock_downstream)
        assert "OPEN" in str(exc_info.value)
        mock_downstream.assert_not_called()

    def test_transition_from_open_to_half_open_after_cooldown(self):
        cb = CircuitBreaker(name="test_cooldown", failure_threshold=2, recovery_timeout=0.1)
        cb.trip()
        assert cb.state == CircuitState.OPEN

        # Sleep past recovery timeout
        time.sleep(0.15)
        # Dynamic check shifts state to HALF_OPEN
        assert cb.state == CircuitState.HALF_OPEN
        assert cb.can_execute() is True

    def test_half_open_probe_success_heals_circuit_to_closed(self):
        cb = CircuitBreaker(name="test_healing", failure_threshold=2, recovery_timeout=0.1)
        cb.trip()
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN

        # Probe succeeds
        def healthy_service():
            return "PONG_HEALTHY"

        result = cb.call(healthy_service)
        assert result == "PONG_HEALTHY"
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute() is True

    def test_half_open_probe_failure_immediately_retrips_to_open(self):
        cb = CircuitBreaker(name="test_re_trip", failure_threshold=2, recovery_timeout=0.1)
        cb.trip()
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN

        # Probe fails
        def still_down_service():
            raise TimeoutError("Still down")

        with pytest.raises(TimeoutError):
            cb.call(still_down_service)

        assert cb.state == CircuitState.OPEN
        assert cb.can_execute() is False

    @pytest.mark.asyncio
    async def test_async_acall_circuit_protection(self):
        cb = CircuitBreaker(name="async_cb", failure_threshold=2, recovery_timeout=1.0)

        async def async_fault():
            raise ValueError("Async DB error")

        with pytest.raises(ValueError):
            await cb.acall(async_fault)
        with pytest.raises(ValueError):
            await cb.acall(async_fault)

        assert cb.state == CircuitState.OPEN

        with pytest.raises(CircuitBreakerOpenException):
            await cb.acall(async_fault)


class TestExponentialBackoffRetry:
    """Test suite for Exponential Backoff with Jitter."""

    def test_sync_retry_succeeds_after_transient_failures(self):
        attempts = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01, max_delay=0.05, jitter=True)
        def unstable_service():
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise ConnectionResetError("Network glitch")
            return "RECOVERED"

        res = unstable_service()
        assert res == "RECOVERED"
        assert attempts == 3

    def test_sync_retry_exhaustion_raises_last_exception(self):
        attempts = 0

        @retry_with_backoff(max_retries=2, base_delay=0.01, max_delay=0.05, jitter=False)
        def dead_service():
            nonlocal attempts
            attempts += 1
            raise TimeoutError("Dead server")

        with pytest.raises(TimeoutError):
            dead_service()
        assert attempts == 3  # 1 initial + 2 retries

    @pytest.mark.asyncio
    async def test_async_retry_succeeds(self):
        attempts = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01, max_delay=0.05, jitter=True)
        async def async_unstable():
            nonlocal attempts
            attempts += 1
            if attempts < 2:
                raise RuntimeError("Redis failover in progress")
            return "SUCCESS"

        res = await async_unstable()
        assert res == "SUCCESS"
        assert attempts == 2


class TestChaosSagaIntegration:
    """Test suite verifying Saga LIFO compensation under Chaos fault injection."""

    @pytest.mark.asyncio
    async def test_saga_lifo_rollback_when_external_service_trips(self):
        """
        Simulate a multi-system business flow:
        Step 1: Create Ticket (OA)
        Step 2: Lock Stock (ERP)
        Step 3: Transfer Budget (Finance) -> Chaos Fault Injected!
        """
        saga = SagaOrchestrator(saga_id="chaos_saga_001")
        compensation_order = []
        mock_state = {}

        # Step 1: OA Ticket
        async def exec_step1(ctx):
            mock_state["ticket_status"] = "CREATED"
            return {"ticket_id": "TICK-9001"}

        async def comp_step1(ctx):
            compensation_order.append("COMPENSATE_STEP1_TICKET")
            mock_state["ticket_status"] = "CANCELLED"

        # Step 2: ERP Inventory Lock
        async def exec_step2(ctx):
            mock_state["inventory_status"] = "LOCKED"
            return {"reserved_qty": 5}

        async def comp_step2(ctx):
            compensation_order.append("COMPENSATE_STEP2_INVENTORY")
            mock_state["inventory_status"] = "RELEASED"

        # Step 3: Finance Budget (Simulate Circuit Breaker OPEN Fault)
        finance_breaker = CircuitBreaker(name="finance_service", failure_threshold=1)
        finance_breaker.trip()  # Injected chaos fault

        async def exec_step3(ctx):
            if not finance_breaker.can_execute():
                raise CircuitBreakerOpenException(
                    service_name="finance_service",
                    message="Finance Service is degraded and circuit is OPEN"
                )
            return {"budget": "transferred"}

        async def comp_step3(ctx):
            compensation_order.append("COMPENSATE_STEP3_BUDGET")

        saga.add_step("OA_Ticket", exec_step1, comp_step1)
        saga.add_step("ERP_Inventory", exec_step2, comp_step2)
        saga.add_step("Finance_Budget", exec_step3, comp_step3)

        with pytest.raises(SagaExecutionError) as exc_info:
            await saga.execute(initial_context={"user_id": "u_999"})

        # Assert Saga detected failure and compensated successfully
        assert saga.status == SagaStatus.COMPENSATED
        assert "Step 'Finance_Budget' failed" in str(exc_info.value)
        assert isinstance(exc_info.value.original_error, CircuitBreakerOpenException)

        # Assert reverse LIFO execution: Step 2 compensated BEFORE Step 1
        assert compensation_order == [
            "COMPENSATE_STEP2_INVENTORY",
            "COMPENSATE_STEP1_TICKET",
        ]
        assert mock_state["inventory_status"] == "RELEASED"
        assert mock_state["ticket_status"] == "CANCELLED"


class TestProductionAdapterChaosProtection:
    """Test suite verifying Production Adapter with Circuit Breaker protection."""

    def test_production_erp_adapter_circuit_breaker_fast_fail(self):
        cb = CircuitBreaker(name="erp_chaos_breaker", failure_threshold=2)
        adapter = ProductionERPAdapter(
            base_url="https://sap.internal.corp",
            circuit_breaker=cb
        )

        # Trip the breaker manually
        cb.trip()
        assert cb.state == CircuitState.OPEN

        # Call adapter
        res = adapter.get_inventory("MacBook Pro")
        assert res["status"] == "CIRCUIT_OPEN"
        assert res["code"] == 503
        assert "is OPEN" in res["message"]

        # Heal breaker
        cb.reset()
        assert cb.state == CircuitState.CLOSED
