"""Production Canary Traffic Controller & Auto-Rollback Engine for Kubernetes/Helm.

Implements NGINX Ingress Canary routing rules:
1. Header-based routing: 'X-Canary: always' -> 100% Canary Pods
2. Cookie-based routing: 'canary_user' -> Canary Pods
3. Weight-based routing: 10% -> 50% -> 100% traffic distribution
4. SRE Health Guardrail: Auto-tripping circuit breaker & zero-downtime rollback on 5xx errors.
"""

from dataclasses import dataclass, field
from enum import Enum
import logging
from pathlib import Path
import random
import time
from typing import Any, Dict, List, Optional
import yaml

logger = logging.getLogger(__name__)


class PodTrack(str, Enum):
    """Deployment Tracks for Traffic Routing."""
    STABLE = "stable"
    CANARY = "canary"


@dataclass
class CanaryConfig:
    """Canary routing and health monitoring configuration."""
    enabled: bool = True
    weight: int = 10  # 0 to 100
    header_enabled: bool = True
    header_name: str = "X-Canary"
    header_value: str = "always"
    cookie_enabled: bool = False
    cookie_name: str = "canary_user"
    error_threshold_percent: float = 5.0  # Max acceptable 5xx percentage
    min_requests_for_eval: int = 5
    auto_rollback_enabled: bool = True


@dataclass
class CanaryResponse:
    """Unified response object from routed Pod clusters."""
    status_code: int
    track: PodTrack
    version: str
    latency_ms: float
    message: str
    headers: Dict[str, str] = field(default_factory=dict)
    rolled_back_active: bool = False


class CanaryController:
    """
    Simulates and manages production-grade Kubernetes Ingress Canary traffic分流.
    Monitors Canary Pod health in real time, automatically trips circuit breaker and
    triggers fast zero-downtime rollbacks when 5xx anomalies are detected.
    """

    def __init__(
        self,
        config: Optional[CanaryConfig] = None,
        stable_version: str = "0.1.0",
        canary_version: str = "0.2.0-canary",
    ):
        self.config = config or CanaryConfig()
        self.stable_version = stable_version
        self.canary_version = canary_version

        # Runtime state
        self.is_rolled_back: bool = False
        self.rollback_reason: Optional[str] = None
        self.canary_fault_injected: bool = False

        # Metrics telemetry
        self.total_requests: int = 0
        self.stable_requests: int = 0
        self.canary_requests: int = 0
        self.stable_errors: int = 0
        self.canary_errors: int = 0
        self.rollback_events: List[Dict[str, Any]] = []

    def set_weight(self, weight: int) -> None:
        """Dynamically adjust Canary traffic weight (0 - 100%)."""
        if not 0 <= weight <= 100:
            raise ValueError(f"Canary weight must be between 0 and 100, got {weight}")
        self.config.weight = weight
        logger.info(f"[CanaryController] Canary traffic weight adjusted to {weight}%.")

    def inject_canary_fault(self, enable: bool = True) -> None:
        """Inject simulated HTTP 500 internal errors into the Canary track for chaos testing."""
        self.canary_fault_injected = enable
        logger.warning(
            f"[CanaryController] Chaos Fault Injection on Canary track set to: {enable}"
        )

    def route_decision(
        self,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
    ) -> PodTrack:
        """
        Evaluate NGINX Ingress Canary routing rules.
        Priority:
        1. Auto-Rollback active or Canary disabled -> STABLE (100%)
        2. Header match (X-Canary: always) -> CANARY (100%)
        3. Cookie match (canary_user) -> CANARY (100%)
        4. Weight probability (0 - 100%) -> CANARY / STABLE
        """
        if self.is_rolled_back or not self.config.enabled:
            return PodTrack.STABLE

        # 1. Header priority check
        if headers and self.config.header_enabled:
            header_val = headers.get(self.config.header_name) or headers.get(
                self.config.header_name.lower()
            )
            if header_val == self.config.header_value:
                return PodTrack.CANARY

        # 2. Cookie priority check
        if cookies and self.config.cookie_enabled:
            if cookies.get(self.config.cookie_name):
                return PodTrack.CANARY

        # 3. Weight-based random distribution
        if self.config.weight <= 0:
            return PodTrack.STABLE
        if self.config.weight >= 100:
            return PodTrack.CANARY

        if random.uniform(0, 100) < self.config.weight:
            return PodTrack.CANARY
        return PodTrack.STABLE

    def handle_request(
        self,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Dict[str, str]] = None,
        failover_on_error: bool = True,
    ) -> CanaryResponse:
        """
        Handle an incoming user request, simulate Pod processing, and monitor health.
        If Canary throws 500 and failover is enabled, immediately fallback to Stable Pod.
        """
        start_time = time.perf_counter()
        target_track = self.route_decision(headers, cookies)
        self.total_requests += 1

        # Simulate Canary execution
        if target_track == PodTrack.CANARY:
            self.canary_requests += 1

            if self.canary_fault_injected:
                self.canary_errors += 1
                logger.error("[CanaryPod] HTTP 500: Injected Fault encountered on Canary node!")

                # Evaluate automated rollback
                if self.config.auto_rollback_enabled:
                    self._check_and_trigger_rollback("Canary Pod encountered critical 500 anomaly")

                if failover_on_error:
                    # Ingress auto-retry fallback to Stable Pod to maintain 100% availability
                    logger.info("[IngressRouter] Canary failed, failover immediately to Baseline!")
                    self.stable_requests += 1
                    elapsed = (time.perf_counter() - start_time) * 1000
                    return CanaryResponse(
                        status_code=200,
                        track=PodTrack.STABLE,
                        version=self.stable_version,
                        latency_ms=elapsed + random.uniform(5.0, 15.0),
                        message="Service OK (Failover from degraded Canary to Baseline)",
                        headers={"X-Upstream-Track": "stable", "X-Failover": "true"},
                        rolled_back_active=self.is_rolled_back,
                    )
                else:
                    elapsed = (time.perf_counter() - start_time) * 1000
                    return CanaryResponse(
                        status_code=500,
                        track=PodTrack.CANARY,
                        version=self.canary_version,
                        latency_ms=elapsed + random.uniform(2.0, 8.0),
                        message="Internal Server Error: Canary Fault",
                        headers={"X-Upstream-Track": "canary"},
                        rolled_back_active=self.is_rolled_back,
                    )

            # Normal Canary processing
            elapsed = (time.perf_counter() - start_time) * 1000
            return CanaryResponse(
                status_code=200,
                track=PodTrack.CANARY,
                version=self.canary_version,
                latency_ms=elapsed + random.uniform(10.0, 30.0),
                message="Service OK from Canary Pod",
                headers={"X-Upstream-Track": "canary"},
                rolled_back_active=self.is_rolled_back,
            )

        # Baseline Stable processing
        self.stable_requests += 1
        elapsed = (time.perf_counter() - start_time) * 1000
        return CanaryResponse(
            status_code=200,
            track=PodTrack.STABLE,
            version=self.stable_version,
            latency_ms=elapsed + random.uniform(8.0, 25.0),
            message="Service OK from Baseline Pod",
            headers={"X-Upstream-Track": "stable"},
            rolled_back_active=self.is_rolled_back,
        )

    def _check_and_trigger_rollback(self, reason: str) -> None:
        """Internal SRE monitor: triggers emergency rollback when error threshold exceeded."""
        if self.is_rolled_back:
            return

        if self.canary_requests >= self.config.min_requests_for_eval:
            error_rate = (self.canary_errors / self.canary_requests) * 100
            if error_rate >= self.config.error_threshold_percent:
                self.trigger_auto_rollback(
                    f"{reason} (Error Rate: {error_rate:.1f}% >= Threshold {self.config.error_threshold_percent}%)"
                )

    def trigger_auto_rollback(self, reason: str) -> None:
        """
        Perform an emergency SRE rollback:
        1. Set Canary weight to 0.
        2. Set is_rolled_back flag to True.
        3. Divert 100% of subsequent traffic to Baseline stable pods.
        """
        self.is_rolled_back = True
        self.rollback_reason = reason
        self.config.weight = 0
        event = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "action": "AUTO_ROLLBACK_TRIPPED",
            "reason": reason,
            "target_weight": 0,
            "canary_requests_before_trip": self.canary_requests,
            "canary_errors_before_trip": self.canary_errors,
        }
        self.rollback_events.append(event)
        logger.critical(
            f"[SRE ALERT] AUTOMATED CANARY ROLLBACK TRIGGERED! Reason: {reason}. "
            f"Traffic diverted 100% back to Baseline."
        )

    def reset_rollback(self, weight: int = 10) -> None:
        """Reset rollback state after SRE intervention and canary patch."""
        self.is_rolled_back = False
        self.rollback_reason = None
        self.canary_fault_injected = False
        self.config.weight = weight
        logger.info(f"[CanaryController] Rollback cleared. Canary resumed at {weight}%.")

    def reset_metrics(self) -> None:
        """Clear telemetry counters for new testing stages."""
        self.total_requests = 0
        self.stable_requests = 0
        self.canary_requests = 0
        self.stable_errors = 0
        self.canary_errors = 0

    def get_metrics(self) -> Dict[str, Any]:
        """Return real-time telemetry metrics."""
        canary_pct = (
            (self.canary_requests / self.total_requests * 100)
            if self.total_requests > 0
            else 0.0
        )
        stable_pct = (
            (self.stable_requests / self.total_requests * 100)
            if self.total_requests > 0
            else 0.0
        )
        canary_err_pct = (
            (self.canary_errors / self.canary_requests * 100)
            if self.canary_requests > 0
            else 0.0
        )

        return {
            "total_requests": self.total_requests,
            "stable_requests": self.stable_requests,
            "canary_requests": self.canary_requests,
            "stable_percentage": round(stable_pct, 2),
            "canary_percentage": round(canary_pct, 2),
            "canary_errors": self.canary_errors,
            "canary_error_percentage": round(canary_err_pct, 2),
            "is_rolled_back": self.is_rolled_back,
            "rollback_reason": self.rollback_reason,
            "configured_weight": self.config.weight,
        }

    @staticmethod
    def audit_helm_ingress_canary(chart_root: Optional[Path] = None) -> Dict[str, Any]:
        """Audit production Helm Chart values.yaml and ingress-canary.yaml template."""
        root = chart_root or Path(__file__).resolve().parent.parent.parent
        helm_dir = root / "deployments" / "helm" / "enterprise-ai"
        values_path = helm_dir / "values.yaml"
        ingress_path = helm_dir / "templates" / "ingress-canary.yaml"

        if not values_path.exists():
            raise FileNotFoundError(f"Missing values.yaml at {values_path}")
        if not ingress_path.exists():
            raise FileNotFoundError(f"Missing ingress-canary.yaml at {ingress_path}")

        with open(values_path, "r", encoding="utf-8") as f:
            values_data = yaml.safe_load(f)

        ingress_content = ingress_path.read_text(encoding="utf-8")

        # Validate annotations
        has_canary_annotation = 'nginx.ingress.kubernetes.io/canary: "true"' in ingress_content
        has_weight_annotation = "nginx.ingress.kubernetes.io/canary-weight:" in ingress_content
        has_header_annotation = "nginx.ingress.kubernetes.io/canary-by-header:" in ingress_content

        canary_val = values_data.get("canary", {})

        return {
            "values_canary_enabled": canary_val.get("enabled", False),
            "values_canary_weight": canary_val.get("weight", 0),
            "values_header_enabled": canary_val.get("header", {}).get("enabled", False),
            "values_header_name": canary_val.get("header", {}).get("name", ""),
            "values_header_value": canary_val.get("header", {}).get("value", ""),
            "has_canary_annotation": has_canary_annotation,
            "has_weight_annotation": has_weight_annotation,
            "has_header_annotation": has_header_annotation,
            "audit_passed": (
                has_canary_annotation
                and has_weight_annotation
                and has_header_annotation
                and canary_val.get("enabled", False)
            ),
        }
