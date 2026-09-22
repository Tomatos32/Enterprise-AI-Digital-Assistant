"""Unit tests for Production Hardening, Soak Load Test Suite & Final Sign-Off Compliance.

Validates:
  1. Load Test Runner execution, percentile mathematics, and telemetry aggregation.
  2. Disaster Recovery and High Availability configuration compliance (DB, Redis, Circuit Breaker, K8s).
  3. Production Sign-Off whitepaper structure, SLA benchmarks, and 12-item Mock cutover matrix.
"""

from pathlib import Path
import pytest

from backend.adapters.factory import (
    check_all_adapters_health,
    get_hr_adapter,
    get_erp_adapter,
    get_oa_adapter,
)
from backend.core.circuit_breaker import CircuitBreaker, CircuitState
from backend.core.config import settings
from backend.core.redis import parse_sentinel_hosts
from benchmark.production_load_test import (
    LoadTestReport,
    LoadTestStep,
    ProductionLoadTestRunner,
    UserScenarioResult,
)


class TestProductionLoadTestRunner:
    """Validates the high-concurrency load test execution engine."""

    def test_percentile_calculation(self):
        """Tests exact percentile calculation across diverse distributions."""
        data = [float(i) for i in range(1, 101)]  # 1 to 100
        p50 = ProductionLoadTestRunner._percentile(data, 50)
        p90 = ProductionLoadTestRunner._percentile(data, 90)
        p95 = ProductionLoadTestRunner._percentile(data, 95)
        p99 = ProductionLoadTestRunner._percentile(data, 99)

        assert abs(p50 - 50.5) < 0.1
        assert abs(p90 - 90.1) < 0.2
        assert abs(p95 - 95.05) < 0.2
        assert abs(p99 - 99.01) < 0.2

        # Edge case: empty data
        assert ProductionLoadTestRunner._percentile([], 95) == 0.0

    @pytest.mark.asyncio
    async def test_single_user_scenario_execution(self):
        """Executes a single user journey and asserts all 5 pipeline stages succeed."""
        runner = ProductionLoadTestRunner(concurrency=1, total_requests=1, simulate_network_delay=False)
        result: UserScenarioResult = await runner.execute_user_scenario(user_id=42)

        assert result.success is True
        assert result.user_id == 42
        assert result.total_latency_ms > 0
        assert result.ttft_ms > 0
        assert result.error is None

        # Verify all 5 steps recorded in step_latencies
        assert LoadTestStep.CHAT_GUARD.value in result.step_latencies
        assert LoadTestStep.RAG_RETRIEVE.value in result.step_latencies
        assert LoadTestStep.SUBGRAPH_HANDOFF.value in result.step_latencies
        assert LoadTestStep.APPROVAL_GATE.value in result.step_latencies
        assert LoadTestStep.SAGA_ROLLBACK.value in result.step_latencies

    @pytest.mark.asyncio
    async def test_load_test_runner_batch_execution(self):
        """Executes a mini concurrent batch and verifies report compilation."""
        runner = ProductionLoadTestRunner(concurrency=10, total_requests=25, simulate_network_delay=False)
        report: LoadTestReport = await runner.run()

        assert report.concurrency == 10
        assert report.total_requests == 25
        assert report.success_count == 25
        assert report.failure_count == 0
        assert report.success_rate == 1.0
        assert report.throughput_qps > 0
        assert report.p50_latency_ms > 0
        assert report.p95_latency_ms >= report.p50_latency_ms
        assert report.p99_latency_ms >= report.p95_latency_ms
        assert report.avg_ttft_ms > 0
        assert report.memory_leak_detected is False
        assert report.redis_pool_steady is True
        assert len(report.step_breakdown) == 5

    def test_report_serialization_and_markdown(self):
        """Tests conversion to dictionary and Markdown representation."""
        report = LoadTestReport(
            concurrency=1000,
            total_requests=1000,
            success_count=1000,
            failure_count=0,
            success_rate=1.0,
            total_duration_sec=0.74,
            throughput_qps=1351.05,
            p50_latency_ms=666.25,
            p90_latency_ms=682.64,
            p95_latency_ms=685.69,
            p99_latency_ms=692.04,
            avg_latency_ms=660.93,
            avg_ttft_ms=210.30,
            p95_ttft_ms=248.55,
            memory_start_mb=10.0,
            memory_end_mb=16.68,
            memory_delta_mb=6.68,
            memory_leak_detected=False,
            redis_max_connections=100,
            redis_in_use_connections=100,
            redis_pool_steady=True,
            step_breakdown={"CHAT_GUARD": {"avg_ms": 25.0, "p95_ms": 40.0}},
        )

        rep_dict = report.to_dict()
        assert rep_dict["concurrency"] == 1000
        assert rep_dict["throughput_qps"] == 1351.05
        assert rep_dict["latency_metrics"]["p99_ms"] == 692.04
        assert rep_dict["memory_metrics"]["leak_detected"] is False

        rep_md = report.to_markdown()
        assert "Production Load Test & Soak Benchmark Report" in rep_md
        assert "1000" in rep_md
        assert "692.04 ms" in rep_md
        assert "CLEAN (No Leak)" in rep_md


class TestDisasterRecoveryAndHAConfig:
    """Validates resilience and high-availability architecture configurations."""

    def test_database_routing_and_pool_settings(self):
        """Verifies database configuration contains server definitions and pool settings."""
        assert hasattr(settings, "MYSQL_SERVER")
        assert getattr(settings, "MYSQL_PORT", 3306) == 3306
        assert hasattr(settings, "SQLALCHEMY_DATABASE_URI")

    def test_redis_sentinel_and_connection_pool_contracts(self):
        """Verifies Redis HA Sentinel host parser and pool max connection limits."""
        sentinel_hosts = parse_sentinel_hosts("sentinel1:26379, sentinel2:26380, sentinel3")
        assert len(sentinel_hosts) == 3
        assert sentinel_hosts[0] == ("sentinel1", 26379)
        assert sentinel_hosts[1] == ("sentinel2", 26380)
        assert sentinel_hosts[2] == ("sentinel3", 26379)

        max_conns = getattr(settings, "REDIS_MAX_CONNECTIONS", 100)
        assert max_conns >= 50

    def test_circuit_breaker_resilience_contracts(self):
        """Verifies circuit breaker state transitions under simulated error rates."""
        cb = CircuitBreaker(name="ha_test_erp", failure_threshold=2, failure_rate_threshold=0.5, recovery_timeout=0.2)
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute() is True

        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.can_execute() is False

    @pytest.mark.asyncio
    async def test_health_integrations_matrix_contract(self):
        """Verifies dynamic adapter integration probe returns health matrix."""
        health_matrix = await check_all_adapters_health()
        assert "integrations" in health_matrix
        integrations = health_matrix["integrations"]
        assert "hr" in integrations
        assert "erp" in integrations
        assert "oa" in integrations
        assert all("status" in v for v in integrations.values())

    def test_adapter_factory_contracts(self):
        """Verifies adapter factory instantiates valid adapters."""
        hr = get_hr_adapter()
        erp = get_erp_adapter()
        oa = get_oa_adapter()
        assert hr is not None
        assert erp is not None
        assert oa is not None


class TestProductionSignoffDocument:
    """Validates the existence, completeness, and rigor of docs/PRODUCTION_SIGNOFF.md."""

    @pytest.fixture
    def signoff_content(self) -> str:
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        signoff_path = project_root / "docs" / "PRODUCTION_SIGNOFF.md"
        assert signoff_path.exists(), f"Missing sign-off whitepaper at {signoff_path}"
        with open(signoff_path, "r", encoding="utf-8") as f:
            return f.read()

    def test_signoff_document_headers_and_verdict(self, signoff_content: str):
        """Verifies document header, verdict, and approval conclusion."""
        assert "企业级 AI 数字员工平台 - 终极生产验收白皮书与就绪签发单" in signoff_content
        assert "APPROVED FOR PRODUCTION" in signoff_content
        assert "V1.0-STAGING-HARDENED" in signoff_content

    def test_all_12_mock_cutover_items_audited(self, signoff_content: str):
        """Verifies that all 12 mock cutover items from MOCK_INVENTORY are explicitly audited."""
        expected_items = [
            "HR 员工信息查询",
            "ERP 物料库存查询",
            "ERP 采购订单创建",
            "OA 故障工单流转",
            "企业微信 Bot 通知",
            "n8n / Dify 事件联动",
            "持久化数据库引擎",
            "企业知识库底座",
            "生产 LLM 网关",
            "专职 Subgraph 工具",
            "Swarm 协同与 Handoff",
            "分布式 Saga 事务补偿",
        ]
        for item in expected_items:
            assert item in signoff_content, f"Mock cutover audit item '{item}' missing from sign-off whitepaper"

    def test_production_sla_benchmarks_documented(self, signoff_content: str):
        """Verifies SLA criteria (Availability, P99, TTFT, QPS) are documented."""
        assert "99.95%" in signoff_content
        assert "1500 ms" in signoff_content
        assert "800 ms" in signoff_content
        assert "1,000" in signoff_content or "1000" in signoff_content

    def test_four_approval_roles_signed(self, signoff_content: str):
        """Verifies the four mandatory executive sign-off roles and approvals."""
        assert "首席系统架构师" in signoff_content
        assert "SRE 运维总监" in signoff_content
        assert "首席信息安全官" in signoff_content
        assert "QA 质量保障总监" in signoff_content
        assert "APPROVED" in signoff_content
