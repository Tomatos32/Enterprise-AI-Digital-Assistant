"""Circuit Breaker State Machine & Resilient Retry Mechanism with Jitter."""

import time
import random
import logging
import asyncio
import functools
from enum import Enum
from typing import Optional, Callable, Any, Type, Tuple, Dict

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit Breaker States."""
    CLOSED = "CLOSED"        # Normal operation: traffic flows freely
    OPEN = "OPEN"            # Tripped: fast fail immediately to prevent cascade
    HALF_OPEN = "HALF_OPEN"  # Cooldown passed: probing downstream recovery


class CircuitBreakerOpenException(Exception):
    """Exception raised when an invocation is rejected because the circuit is OPEN."""
    def __init__(
        self,
        service_name: str = "default",
        state: str = "OPEN",
        message: Optional[str] = None
    ):
        self.service_name = service_name
        self.state = state
        self.message = message or (
            f"CircuitBreaker [{service_name}] is OPEN. "
            f"Downstream service is degraded, fast-failing to prevent avalanche."
        )
        super().__init__(self.message)


class CircuitBreaker:
    """
    Production-grade three-state Circuit Breaker state machine.
    Monitors failure rates, trips to OPEN when error rate > threshold,
    and transitions to HALF_OPEN after recovery_timeout to probe self-healing.
    """

    def __init__(
        self,
        name: str = "default",
        failure_threshold: int = 4,
        failure_rate_threshold: float = 0.5,
        recovery_timeout: float = 2.0,
        half_open_max_calls: int = 1,
        expected_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    ):
        """
        :param name: Identifier of the downstream target (e.g. 'erp_adapter')
        :param failure_threshold: Min calls required in window before evaluating error rate
        :param failure_rate_threshold: Ratio of failures (e.g. 0.5 = 50%) to trip breaker
        :param recovery_timeout: Cooldown window in seconds before attempting HALF_OPEN probe
        :param half_open_max_calls: Max number of probe calls allowed in HALF_OPEN
        :param expected_exceptions: Exceptions considered as system failures
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.failure_rate_threshold = failure_rate_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.expected_exceptions = expected_exceptions

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._total_calls = 0
        self._last_state_change = time.time()
        self._half_open_calls = 0

    @property
    def state(self) -> CircuitState:
        """Dynamic state getter with automated OPEN -> HALF_OPEN cooldown transition."""
        if self._state == CircuitState.OPEN:
            elapsed = time.time() - self._last_state_change
            if elapsed >= self.recovery_timeout:
                logger.info(
                    f"[CircuitBreaker:{self.name}] Cooldown ({self.recovery_timeout}s) expired. "
                    f"Transitioning from OPEN -> HALF_OPEN."
                )
                self._state = CircuitState.HALF_OPEN
                self._last_state_change = time.time()
                self._half_open_calls = 0
        return self._state

    def can_execute(self) -> bool:
        """Determines if a call can proceed based on current state."""
        current_state = self.state
        if current_state == CircuitState.CLOSED:
            return True
        elif current_state == CircuitState.OPEN:
            return False
        elif current_state == CircuitState.HALF_OPEN:
            if self._half_open_calls < self.half_open_max_calls:
                self._half_open_calls += 1
                return True
            return False
        return False

    def record_success(self) -> None:
        """Records a successful invocation."""
        current_state = self.state
        if current_state == CircuitState.HALF_OPEN:
            logger.info(
                f"[CircuitBreaker:{self.name}] Probe call succeeded! "
                f"Transitioning from HALF_OPEN -> CLOSED (System Healed)."
            )
            self._state = CircuitState.CLOSED
            self._last_state_change = time.time()
            self._reset_counts()
        elif current_state == CircuitState.CLOSED:
            self._success_count += 1
            self._total_calls += 1

    def record_failure(self, exc: Optional[Exception] = None) -> None:
        """Records a failed invocation and evaluates trip conditions."""
        current_state = self.state
        if current_state == CircuitState.HALF_OPEN:
            logger.warning(
                f"[CircuitBreaker:{self.name}] Probe call failed with {type(exc).__name__}. "
                f"Immediately re-tripping from HALF_OPEN -> OPEN."
            )
            self._state = CircuitState.OPEN
            self._last_state_change = time.time()
            self._half_open_calls = 0
        elif current_state == CircuitState.CLOSED:
            self._failure_count += 1
            self._total_calls += 1
            failure_rate = self._failure_count / max(1, self._total_calls)

            # Trip if minimum threshold reached and error rate exceeded
            if (
                self._total_calls >= self.failure_threshold
                and failure_rate >= self.failure_rate_threshold
            ) or (self._failure_count >= self.failure_threshold):
                logger.error(
                    f"[CircuitBreaker:{self.name}] Error rate ({failure_rate:.1%}) or consecutive "
                    f"failures ({self._failure_count}) exceeded threshold! "
                    f"Tripping circuit: CLOSED -> OPEN."
                )
                self._state = CircuitState.OPEN
                self._last_state_change = time.time()

    def _reset_counts(self) -> None:
        """Resets sliding window counters."""
        self._failure_count = 0
        self._success_count = 0
        self._total_calls = 0
        self._half_open_calls = 0

    def reset(self) -> None:
        """Manually forces breaker reset to healthy CLOSED state."""
        self._state = CircuitState.CLOSED
        self._last_state_change = time.time()
        self._reset_counts()

    def trip(self) -> None:
        """Manually forces breaker to trip into OPEN state (e.g. for Chaos drills)."""
        self._state = CircuitState.OPEN
        self._last_state_change = time.time()
        self._half_open_calls = 0

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Synchronous wrapper execution with circuit protection."""
        if not self.can_execute():
            raise CircuitBreakerOpenException(service_name=self.name, state=self.state.value)

        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        except self.expected_exceptions as e:
            self.record_failure(e)
            raise

    async def acall(self, coro_func: Callable, *args, **kwargs) -> Any:
        """Asynchronous wrapper execution with circuit protection."""
        if not self.can_execute():
            raise CircuitBreakerOpenException(service_name=self.name, state=self.state.value)

        try:
            result = await coro_func(*args, **kwargs)
            self.record_success()
            return result
        except self.expected_exceptions as e:
            self.record_failure(e)
            raise

    def __call__(self, func: Callable) -> Callable:
        """Decorator support for both sync and async functions."""
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await self.acall(func, *args, **kwargs)
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                return self.call(func, *args, **kwargs)
            return sync_wrapper


# Global Circuit Breaker Registry
_CIRCUIT_BREAKERS: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    name: str = "default",
    failure_threshold: int = 4,
    failure_rate_threshold: float = 0.5,
    recovery_timeout: float = 2.0,
    half_open_max_calls: int = 1,
) -> CircuitBreaker:
    """Retrieves or creates a singleton CircuitBreaker instance for the service name."""
    if name not in _CIRCUIT_BREAKERS:
        _CIRCUIT_BREAKERS[name] = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            failure_rate_threshold=failure_rate_threshold,
            recovery_timeout=recovery_timeout,
            half_open_max_calls=half_open_max_calls,
        )
    return _CIRCUIT_BREAKERS[name]


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 0.05,
    max_delay: float = 1.0,
    jitter: bool = True,
    retry_exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable:
    """
    Decorator implementing Exponential Backoff with Jitter for resilient retry.
    Supports both synchronous and asynchronous functions.
    """
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapped(*args, **kwargs):
                attempt = 0
                while True:
                    try:
                        return await func(*args, **kwargs)
                    except retry_exceptions as e:
                        attempt += 1
                        if attempt > max_retries:
                            logger.error(
                                f"[Retry] Max retries ({max_retries}) exhausted for async {func.__name__}."
                            )
                            raise e

                        delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
                        if jitter:
                            delay += random.uniform(0, base_delay)

                        logger.warning(
                            f"[Retry] Attempt {attempt}/{max_retries} for {func.__name__} failed: "
                            f"{type(e).__name__} - {str(e)}. Retrying in {delay:.3f}s..."
                        )
                        await asyncio.sleep(delay)
            return async_wrapped
        else:
            @functools.wraps(func)
            def sync_wrapped(*args, **kwargs):
                attempt = 0
                while True:
                    try:
                        return func(*args, **kwargs)
                    except retry_exceptions as e:
                        attempt += 1
                        if attempt > max_retries:
                            logger.error(
                                f"[Retry] Max retries ({max_retries}) exhausted for sync {func.__name__}."
                            )
                            raise e

                        delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
                        if jitter:
                            delay += random.uniform(0, base_delay)

                        logger.warning(
                            f"[Retry] Attempt {attempt}/{max_retries} for {func.__name__} failed: "
                            f"{type(e).__name__} - {str(e)}. Retrying in {delay:.3f}s..."
                        )
                        time.sleep(delay)
            return sync_wrapped
    return decorator
