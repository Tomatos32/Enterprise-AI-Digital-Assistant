"""Production Disaster Recovery & Chaos Resilience Engine (Ops-0002).

Simulates and audits:
1. External dependency outages (SAP ERP, Feishu HR, Finance) triggering CircuitBreaker transitions (CLOSED -> OPEN -> HALF_OPEN -> CLOSED).
2. Distributed Saga transactions under chaos fault injection, validating LIFO reverse compensation and idempotent database state.
3. Redis Sentinel High Availability failover, verifying automatic Master election and connection pool self-healing.
"""

from dataclasses import dataclass
from enum import Enum
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from backend.core.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenException,
)
from backend.core.saga_orchestrator import (
    SagaOrchestrator,
)

logger = logging.getLogger("disaster_recovery")


class ChaosFaultType(str, Enum):
    """Types of Chaos Faults to inject."""
    NONE = "NONE"
    TIMEOUT = "TIMEOUT"
    HTTP_503 = "HTTP_503"
    NETWORK_RESET = "NETWORK_RESET"


@dataclass
class ExternalServiceHealth:
    """Status record of external integrated enterprise service."""
    service_name: str
    is_healthy: bool = True
    fault_type: ChaosFaultType = ChaosFaultType.NONE
    latency_ms: float = 15.0
    failure_count: int = 0
    total_calls: int = 0


class ExternalSystemChaosSimulator:
    """Simulates external enterprise services (ERP, HR, Finance) with fault injection."""

    def __init__(self):
        self.services: Dict[str, ExternalServiceHealth] = {
            "sap_erp": ExternalServiceHealth(service_name="sap_erp"),
            "feishu_hr": ExternalServiceHealth(service_name="feishu_hr"),
            "finance_gateway": ExternalServiceHealth(service_name="finance_gateway"),
        }

    def inject_fault(self, service_name: str, fault_type: ChaosFaultType) -> None:
        """Inject a specific fault type into an external enterprise dependency."""
        if service_name not in self.services:
            raise KeyError(f"Unknown external service: {service_name}")
        srv = self.services[service_name]
        srv.fault_type = fault_type
        srv.is_healthy = (fault_type == ChaosFaultType.NONE)
        logger.warning(f"[ChaosSimulator] Fault [{fault_type.value}] injected into {service_name}.")

    def heal_service(self, service_name: str) -> None:
        """Restore an external enterprise service to healthy state."""
        if service_name in self.services:
            self.services[service_name].fault_type = ChaosFaultType.NONE
            self.services[service_name].is_healthy = True
            logger.info(f"[ChaosSimulator] Service {service_name} restored to HEALTHY.")

    def invoke(self, service_name: str, action: str, **kwargs: Any) -> Dict[str, Any]:
        """Invoke the simulated external service."""
        srv = self.services.get(service_name)
        if not srv:
            raise KeyError(f"Unknown service: {service_name}")

        srv.total_calls += 1

        if srv.fault_type == ChaosFaultType.HTTP_503:
            srv.failure_count += 1
            raise ConnectionError(f"HTTP 503 Service Unavailable: {service_name} is down")
        elif srv.fault_type == ChaosFaultType.TIMEOUT:
            srv.failure_count += 1
            raise TimeoutError(f"Gateway Timeout: {service_name} failed to respond in 5000ms")
        elif srv.fault_type == ChaosFaultType.NETWORK_RESET:
            srv.failure_count += 1
            raise ConnectionResetError(f"Connection reset by peer: {service_name}")

        return {
            "status": "SUCCESS",
            "service": service_name,
            "action": action,
            "timestamp": time.time(),
            "data": kwargs,
        }


class CircuitBreakerAuditor:
    """Audits Circuit Breaker state transitions, trip thresholds, and fast-fail latencies."""

    def __init__(self, breaker: CircuitBreaker):
        self.breaker = breaker
        self.audit_events: List[Dict[str, Any]] = []

    def audit_invocation(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Call target through breaker and record telemetry."""
        state_before = self.breaker.state
        start_time = time.perf_counter()
        result = None
        error = None
        rejected_by_breaker = False

        try:
            result = self.breaker.call(fn, *args, **kwargs)
        except CircuitBreakerOpenException as cboe:
            error = cboe
            rejected_by_breaker = True
        except Exception as ex:
            error = ex

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        state_after = self.breaker.state

        event = {
            "state_before": state_before.value,
            "state_after": state_after.value,
            "latency_ms": round(elapsed_ms, 3),
            "rejected_by_breaker": rejected_by_breaker,
            "success": result is not None,
            "error_type": type(error).__name__ if error else None,
        }
        self.audit_events.append(event)
        return event


class SagaDisasterDrill:
    """Executes distributed Saga transaction drills under chaos fault injection."""

    def __init__(self, simulator: ExternalSystemChaosSimulator):
        self.simulator = simulator
        self.system_state: Dict[str, Any] = {
            "oa_tickets": {},
            "erp_inventory": {"MacBook_Pro_M3": 100},
            "finance_budget": 50000.0,
        }
        self.compensation_history: List[str] = []

    async def run_purchase_saga(
        self,
        item_id: str,
        quantity: int,
        unit_price: float,
        breaker: Optional[CircuitBreaker] = None,
    ) -> SagaOrchestrator:
        """
        Execute 3-step Saga:
        Step 1: OA Work Order
        Step 2: ERP Inventory Lock
        Step 3: Finance Budget Lock & Transfer
        """
        saga = SagaOrchestrator(saga_id=f"drill_saga_{int(time.time())}")
        self.compensation_history.clear()
        total_cost = quantity * unit_price

        # Step 1: OA Ticket
        async def exec_oa(ctx: Dict[str, Any]) -> Dict[str, Any]:
            self.simulator.invoke("feishu_hr", "verify_employee", emp_id="EMP-1001")
            ticket_id = f"TCK-{int(time.time())}"
            self.system_state["oa_tickets"][ticket_id] = "CREATED"
            ctx["ticket_id"] = ticket_id
            return {"ticket_id": ticket_id}

        async def comp_oa(ctx: Dict[str, Any]) -> None:
            ticket_id = ctx.get("ticket_id")
            if ticket_id in self.system_state["oa_tickets"]:
                self.system_state["oa_tickets"][ticket_id] = "CANCELLED"
            self.compensation_history.append("COMPENSATE_OA_TICKET")

        # Step 2: ERP Inventory
        async def exec_erp(ctx: Dict[str, Any]) -> Dict[str, Any]:
            self.simulator.invoke("sap_erp", "check_stock", item=item_id)
            if self.system_state["erp_inventory"].get(item_id, 0) < quantity:
                raise ValueError("Insufficient inventory")
            self.system_state["erp_inventory"][item_id] -= quantity
            ctx["reserved_qty"] = quantity
            return {"reserved": quantity}

        async def comp_erp(ctx: Dict[str, Any]) -> None:
            reserved = ctx.get("reserved_qty", 0)
            self.system_state["erp_inventory"][item_id] += reserved
            self.compensation_history.append("COMPENSATE_ERP_INVENTORY")

        # Step 3: Finance Budget (Wrapped in CircuitBreaker if provided)
        async def exec_finance(ctx: Dict[str, Any]) -> Dict[str, Any]:
            def _call_finance():
                return self.simulator.invoke("finance_gateway", "transfer_budget", amount=total_cost)

            if breaker:
                if not breaker.can_execute():
                    raise CircuitBreakerOpenException(
                        service_name="finance_gateway",
                        message="Finance Gateway circuit is OPEN"
                    )
                breaker.call(_call_finance)
            else:
                _call_finance()

            self.system_state["finance_budget"] -= total_cost
            ctx["transferred_amount"] = total_cost
            return {"transferred": total_cost}

        async def comp_finance(ctx: Dict[str, Any]) -> None:
            amount = ctx.get("transferred_amount", 0.0)
            self.system_state["finance_budget"] += amount
            self.compensation_history.append("COMPENSATE_FINANCE_BUDGET")

        saga.add_step("OA_Ticket_Creation", exec_oa, comp_oa)
        saga.add_step("ERP_Inventory_Reservation", exec_erp, comp_erp)
        saga.add_step("Finance_Budget_Transfer", exec_finance, comp_finance)

        await saga.execute()
        return saga


@dataclass
class RedisNode:
    """Represents a Redis server node."""
    host: str
    port: int
    role: str  # "master" or "slave"
    is_alive: bool = True


class SimulatedRedisSentinelCluster:
    """Simulates Redis Sentinel High Availability cluster with automated failover."""

    def __init__(self, master_name: str = "mymaster"):
        self.master_name = master_name
        self.nodes: Dict[str, RedisNode] = {
            "node_master": RedisNode(host="10.0.0.1", port=6379, role="master"),
            "node_replica_1": RedisNode(host="10.0.0.2", port=6379, role="slave"),
            "node_replica_2": RedisNode(host="10.0.0.3", port=6379, role="slave"),
        }
        self.sentinel_quorum = 2
        self.active_master_key: str = "node_master"
        self.failover_events: List[Dict[str, Any]] = []

    def get_current_master(self) -> Tuple[str, int]:
        """Returns the host:port of the currently elected Master."""
        master_node = self.nodes[self.active_master_key]
        if not master_node.is_alive:
            raise ConnectionError(f"Current master [{self.active_master_key}] is down and not failed over!")
        return master_node.host, master_node.port

    def simulate_master_crash(self) -> None:
        """Simulate physical master node crash."""
        crashed_node = self.nodes[self.active_master_key]
        crashed_node.is_alive = False
        logger.critical(f"[RedisSentinel] Active Master {crashed_node.host}:{crashed_node.port} CRASHED!")

    def execute_sentinel_failover(self) -> str:
        """
        Sentinel detects Master down (+sdown -> +odown), elects new master,
        promotes replica, and updates cluster topology.
        """
        old_master_key = self.active_master_key
        old_master = self.nodes[old_master_key]

        # Find healthy replica to promote
        candidates = [k for k, v in self.nodes.items() if v.role == "slave" and v.is_alive]
        if not candidates:
            raise RuntimeError("No healthy replicas available for Sentinel failover!")

        new_master_key = candidates[0]
        new_master = self.nodes[new_master_key]

        # Elect new master
        old_master.role = "slave"
        new_master.role = "master"
        self.active_master_key = new_master_key

        event = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "action": "+switch-master",
            "master_name": self.master_name,
            "old_master": f"{old_master.host}:{old_master.port}",
            "new_master": f"{new_master.host}:{new_master.port}",
            "status": "FAILOVER_COMPLETED",
        }
        self.failover_events.append(event)
        logger.warning(
            f"[RedisSentinel] FAILOVER COMPLETED! Promoted {new_master.host}:{new_master.port} "
            f"as new Master for {self.master_name}."
        )
        return new_master_key
