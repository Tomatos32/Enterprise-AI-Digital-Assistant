"""Unit tests for Canary Rollout, Ingress Header Routing, and SRE Auto-Rollback."""

from pathlib import Path
import pytest
from backend.ops.canary_controller import (
    CanaryConfig,
    CanaryController,
    PodTrack,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def test_helm_chart_canary_audit():
    """Verify CanaryController audits enterprise-ai Helm chart templates and values."""
    audit = CanaryController.audit_helm_ingress_canary(REPO_ROOT)
    assert audit["audit_passed"] is True
    assert audit["values_canary_enabled"] is True
    assert audit["values_canary_weight"] == 10
    assert audit["values_header_name"] == "X-Canary"
    assert audit["values_header_value"] == "always"
    assert audit["has_canary_annotation"] is True
    assert audit["has_weight_annotation"] is True
    assert audit["has_header_annotation"] is True


def test_canary_header_routing_override():
    """Verify X-Canary header bypasses weight and forces 100% traffic to Canary."""
    # Even if weight is 0, header override must route to Canary
    config = CanaryConfig(enabled=True, weight=0, header_enabled=True)
    controller = CanaryController(config=config)

    for _ in range(50):
        resp = controller.handle_request(headers={"X-Canary": "always"})
        assert resp.track == PodTrack.CANARY
        assert resp.version == "0.2.0-canary"
        assert resp.status_code == 200

    metrics = controller.get_metrics()
    assert metrics["canary_percentage"] == 100.0
    assert metrics["stable_requests"] == 0


def test_canary_weight_boundaries():
    """Verify weight 0% routes strictly to Stable and 100% routes strictly to Canary."""
    controller = CanaryController()

    # Weight 0
    controller.set_weight(0)
    for _ in range(50):
        resp = controller.handle_request()
        assert resp.track == PodTrack.STABLE
        assert resp.version == "0.1.0"

    # Weight 100
    controller.set_weight(100)
    for _ in range(50):
        resp = controller.handle_request()
        assert resp.track == PodTrack.CANARY
        assert resp.version == "0.2.0-canary"


def test_canary_progressive_distribution_10_percent():
    """Verify 10% canary traffic falls within statistical binomial tolerance."""
    controller = CanaryController(config=CanaryConfig(weight=10))
    for _ in range(1000):
        controller.handle_request()

    metrics = controller.get_metrics()
    # Expected 10%, 99% binomial tolerance: 6% <= ratio <= 14%
    assert 6.0 <= metrics["canary_percentage"] <= 14.0


def test_canary_progressive_distribution_50_percent():
    """Verify 50% canary traffic falls within statistical binomial tolerance."""
    controller = CanaryController(config=CanaryConfig(weight=50))
    for _ in range(1000):
        controller.handle_request()

    metrics = controller.get_metrics()
    # Expected 50%, 99% binomial tolerance: 44% <= ratio <= 56%
    assert 44.0 <= metrics["canary_percentage"] <= 56.0


def test_canary_chaos_500_fault_injection_and_failover():
    """Verify Canary fault injection triggers Ingress upstream failover to Baseline."""
    controller = CanaryController(config=CanaryConfig(weight=100))
    controller.inject_canary_fault(True)

    # With failover enabled, user receives HTTP 200 from baseline
    resp = controller.handle_request(failover_on_error=True)
    assert resp.status_code == 200
    assert resp.track == PodTrack.STABLE
    assert resp.headers.get("X-Failover") == "true"
    assert controller.canary_errors == 1


def test_canary_auto_rollback_trips_circuit_breaker():
    """Verify consecutive Canary errors trip auto-rollback and zero out weight."""
    config = CanaryConfig(
        weight=50,
        error_threshold_percent=5.0,
        min_requests_for_eval=3,
        auto_rollback_enabled=True,
    )
    controller = CanaryController(config=config)
    controller.inject_canary_fault(True)

    # Send requests to trigger threshold (sufficient iterations to guarantee min_requests_for_eval=3 under 50% probability)
    for _ in range(30):
        controller.handle_request(failover_on_error=True)

    assert controller.is_rolled_back is True
    assert controller.config.weight == 0
    assert "Canary Pod encountered critical 500 anomaly" in controller.rollback_reason
    assert len(controller.rollback_events) >= 1
    assert controller.rollback_events[0]["action"] == "AUTO_ROLLBACK_TRIPPED"


def test_canary_post_rollback_traffic_guarantee():
    """Verify that after auto-rollback, 100% of subsequent requests route to Baseline."""
    controller = CanaryController(config=CanaryConfig(weight=50))
    controller.trigger_auto_rollback("Simulated critical degradation")

    assert controller.is_rolled_back is True
    assert controller.config.weight == 0

    # Test 100 subsequent requests
    for _ in range(100):
        resp = controller.handle_request()
        assert resp.status_code == 200
        assert resp.track == PodTrack.STABLE
        assert resp.version == "0.1.0"
        assert resp.rolled_back_active is True


def test_canary_reset_rollback_recovery():
    """Verify SRE can reset rollback after patching Canary version."""
    controller = CanaryController(config=CanaryConfig(weight=50))
    controller.trigger_auto_rollback("Outage")
    assert controller.is_rolled_back is True

    # SRE resolves issue and resets rollback to 10%
    controller.reset_rollback(weight=10)
    assert controller.is_rolled_back is False
    assert controller.config.weight == 10
    assert controller.rollback_reason is None
    assert controller.canary_fault_injected is False


def test_canary_cookie_routing():
    """Verify cookie-based canary routing when enabled."""
    config = CanaryConfig(weight=0, cookie_enabled=True, cookie_name="canary_user")
    controller = CanaryController(config=config)

    # Without cookie -> Stable
    resp1 = controller.handle_request()
    assert resp1.track == PodTrack.STABLE

    # With cookie -> Canary
    resp2 = controller.handle_request(cookies={"canary_user": "tester_01"})
    assert resp2.track == PodTrack.CANARY
    assert resp2.version == "0.2.0-canary"


def test_canary_invalid_weight_validation():
    """Verify setting out-of-range weight raises ValueError."""
    controller = CanaryController()
    with pytest.raises(ValueError, match="between 0 and 100"):
        controller.set_weight(150)

    with pytest.raises(ValueError, match="between 0 and 100"):
        controller.set_weight(-5)
