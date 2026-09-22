"""Unit tests for Disaster Recovery, Circuit Breaker Auditing, and Redis Sentinel Failover (Ops-0002)."""

import time
import pytest
from backend.core.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenException,
    CircuitState,
)
from backend.core.saga_orchestrator import SagaExecutionError
from backend.ops.disaster_recovery import (
    ChaosFaultType,
    CircuitBreakerAuditor,
    ExternalSystemChaosSimulator,
    SagaDisasterDrill,
    SimulatedRedisSentinelCluster,
)
from benchmark.disaster_recovery_drill import run_disaster_recovery_drill


def test_external_chaos_simulator_fault_injection():
    """Verify ExternalSystemChaosSimulator correctly throws injected fault types."""
    sim = ExternalSystemChaosSimulator()

    # Normal
    res = sim.invoke("sap_erp", "get_material")
    assert res["status"] == "SUCCESS"

    # HTTP 503
    sim.inject_fault("sap_erp", ChaosFaultType.HTTP_503)
    with pytest.raises(ConnectionError, match="HTTP 503"):
        sim.invoke("sap_erp", "get_material")

    # Timeout
    sim.inject_fault("feishu_hr", ChaosFaultType.TIMEOUT)
    with pytest.raises(TimeoutError, match="Gateway Timeout"):
        sim.invoke("feishu_hr", "get_employee")

    # Heal
    sim.heal_service("sap_erp")
    res2 = sim.invoke("sap_erp", "get_material")
    assert res2["status"] == "SUCCESS"


def test_circuit_breaker_closed_to_open_transition():
    """Verify CircuitBreaker transitions from CLOSED to OPEN after meeting threshold."""
    cb = CircuitBreaker(name="test_cb", failure_threshold=3, recovery_timeout=0.2)
    auditor = CircuitBreakerAuditor(cb)
    sim = ExternalSystemChaosSimulator()
    sim.inject_fault("sap_erp", ChaosFaultType.HTTP_503)

    for _ in range(3):
        auditor.audit_invocation(sim.invoke, "sap_erp", "test")

    assert cb.state == CircuitState.OPEN
    assert len(auditor.audit_events) == 3
    assert auditor.audit_events[-1]["state_after"] == "OPEN"


def test_circuit_breaker_fast_fail_zero_downstream_calls():
    """Verify CircuitBreaker rejects calls with 0 downstream calls when OPEN."""
    cb = CircuitBreaker(name="fast_fail_cb", failure_threshold=1)
    cb.trip()
    assert cb.state == CircuitState.OPEN

    auditor = CircuitBreakerAuditor(cb)
    sim = ExternalSystemChaosSimulator()
    calls_before = sim.services["sap_erp"].total_calls

    ev = auditor.audit_invocation(sim.invoke, "sap_erp", "test")
    calls_after = sim.services["sap_erp"].total_calls

    assert ev["rejected_by_breaker"] is True
    assert ev["error_type"] == "CircuitBreakerOpenException"
    assert calls_after == calls_before
    assert ev["latency_ms"] < 5.0  # Must be fast-fail


def test_circuit_breaker_dynamic_half_open_and_healing():
    """Verify transition from OPEN -> HALF_OPEN -> CLOSED after probe success."""
    cb = CircuitBreaker(name="heal_cb", failure_threshold=1, recovery_timeout=0.05)
    cb.trip()
    assert cb.state == CircuitState.OPEN

    time.sleep(0.08)
    # Dynamic check shifts to HALF_OPEN
    assert cb.state == CircuitState.HALF_OPEN

    auditor = CircuitBreakerAuditor(cb)
    sim = ExternalSystemChaosSimulator()
    ev = auditor.audit_invocation(sim.invoke, "sap_erp", "test")

    assert ev["success"] is True
    assert cb.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_saga_disaster_drill_lifo_reverse_compensation():
    """Verify distributed Saga executes strict LIFO reverse compensation under chaos."""
    sim = ExternalSystemChaosSimulator()
    drill = SagaDisasterDrill(sim)

    breaker = CircuitBreaker(name="finance_cb", failure_threshold=1)
    breaker.trip()  # Injected chaos fault

    with pytest.raises(SagaExecutionError) as exc_info:
        await drill.run_purchase_saga("MacBook_Pro_M3", 2, 1500.0, breaker=breaker)

    assert "Step 'Finance_Budget_Transfer' failed" in str(exc_info.value)
    assert isinstance(exc_info.value.original_error, CircuitBreakerOpenException)

    # Assert strict LIFO: Inventory compensated before OA ticket
    assert drill.compensation_history == [
        "COMPENSATE_ERP_INVENTORY",
        "COMPENSATE_OA_TICKET",
    ]


@pytest.mark.asyncio
async def test_saga_disaster_drill_idempotent_state_restoration():
    """Verify database and business state is 100% restored after compensation."""
    sim = ExternalSystemChaosSimulator()
    drill = SagaDisasterDrill(sim)

    init_stock = drill.system_state["erp_inventory"]["MacBook_Pro_M3"]
    init_budget = drill.system_state["finance_budget"]

    breaker = CircuitBreaker(name="finance_cb", failure_threshold=1)
    breaker.trip()

    with pytest.raises(SagaExecutionError):
        await drill.run_purchase_saga("MacBook_Pro_M3", 10, 1000.0, breaker=breaker)

    final_stock = drill.system_state["erp_inventory"]["MacBook_Pro_M3"]
    final_budget = drill.system_state["finance_budget"]

    assert final_stock == init_stock
    assert final_budget == init_budget
    # All tickets must be cancelled
    for ticket_status in drill.system_state["oa_tickets"].values():
        assert ticket_status == "CANCELLED"


def test_redis_sentinel_failover_simulation():
    """Verify Redis Sentinel detects master down and elects replica as new Master."""
    cluster = SimulatedRedisSentinelCluster(master_name="test_master")
    old_host, old_port = cluster.get_current_master()
    assert (old_host, old_port) == ("10.0.0.1", 6379)

    # Crash master
    cluster.simulate_master_crash()
    with pytest.raises(ConnectionError, match="is down"):
        cluster.get_current_master()

    # Sentinel promotes replica
    new_master_key = cluster.execute_sentinel_failover()
    new_host, new_port = cluster.get_current_master()

    assert (new_host, new_port) == ("10.0.0.2", 6379)
    assert cluster.nodes[new_master_key].role == "master"
    assert len(cluster.failover_events) == 1
    assert cluster.failover_events[0]["action"] == "+switch-master"


def test_redis_sentinel_no_healthy_replica_raises_error():
    """Verify Sentinel raises error when all replicas are down."""
    cluster = SimulatedRedisSentinelCluster()
    cluster.nodes["node_replica_1"].is_alive = False
    cluster.nodes["node_replica_2"].is_alive = False

    cluster.simulate_master_crash()
    with pytest.raises(RuntimeError, match="No healthy replicas"):
        cluster.execute_sentinel_failover()


@pytest.mark.asyncio
async def test_full_integrated_disaster_recovery_drill():
    """Verify full end-to-end benchmark drill script completes all 3 scenarios."""
    summary = await run_disaster_recovery_drill(output_json=False)
    assert summary["scenarios"]["scenario_1_circuit_breaker"]["status"] == "PASSED"
    assert summary["scenarios"]["scenario_2_saga_compensation"]["status"] == "PASSED"
    assert summary["scenarios"]["scenario_3_redis_sentinel"]["status"] == "PASSED"
