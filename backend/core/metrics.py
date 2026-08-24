"""Prometheus Metrics Collector Module for Enterprise AI Digital Assistant.

Defines production-grade Prometheus metrics for LLM token usage, TTFT latency,
cache hits/misses, active WebSocket connections, and Celery queue depth.
"""

from typing import Union
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
    REGISTRY,
)

# 1. LLM Token Usage Counter
llm_token_total = Counter(
    "llm_token_total",
    "Total number of tokens consumed by LLM models",
    ["model", "type"],  # type: 'input' | 'output'
)

# 2. Time to First Token (TTFT) Histogram (seconds)
llm_time_to_first_token_seconds = Histogram(
    "llm_time_to_first_token_seconds",
    "Time to first token (TTFT) latency for LLM streaming responses in seconds",
    buckets=(0.02, 0.05, 0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0),
)

# 3. Prompt Cache Hit / Miss Counters
prompt_cache_hits_total = Counter(
    "prompt_cache_hits_total",
    "Total number of LLM prompt cache hits",
)

prompt_cache_misses_total = Counter(
    "prompt_cache_misses_total",
    "Total number of LLM prompt cache misses",
)

# 4. Active WebSocket Connections Gauge
active_websocket_connections = Gauge(
    "active_websocket_connections",
    "Current number of active real-time WebSocket client connections",
)

# 5. Celery Queue Depth Gauge
celery_queue_depth = Gauge(
    "celery_queue_depth",
    "Current depth / pending task count in Celery worker queues",
)


def record_llm_tokens(model: str, token_type: str, count: Union[int, float] = 1) -> None:
    """Record LLM token consumption by model and type (input/output)."""
    llm_token_total.labels(model=model, type=token_type).inc(count)


def record_ttft(seconds: float) -> None:
    """Record Time to First Token (TTFT) in seconds."""
    llm_time_to_first_token_seconds.observe(seconds)


def record_cache_hit(count: int = 1) -> None:
    """Increment prompt cache hit counter."""
    prompt_cache_hits_total.inc(count)


def record_cache_miss(count: int = 1) -> None:
    """Increment prompt cache miss counter."""
    prompt_cache_misses_total.inc(count)


def set_active_ws_connections(count: int) -> None:
    """Set the number of active WebSocket connections."""
    active_websocket_connections.set(count)


def inc_active_ws_connections() -> None:
    """Increment active WebSocket connections count by 1."""
    active_websocket_connections.inc()


def dec_active_ws_connections() -> None:
    """Decrement active WebSocket connections count by 1."""
    active_websocket_connections.dec()


def set_celery_queue_depth(depth: int) -> None:
    """Set current Celery queue depth."""
    celery_queue_depth.set(depth)


def get_metrics_payload() -> bytes:
    """Generate Prometheus metric scrape payload."""
    return generate_latest(REGISTRY)


__all__ = [
    "llm_token_total",
    "llm_time_to_first_token_seconds",
    "prompt_cache_hits_total",
    "prompt_cache_misses_total",
    "active_websocket_connections",
    "celery_queue_depth",
    "record_llm_tokens",
    "record_ttft",
    "record_cache_hit",
    "record_cache_miss",
    "set_active_ws_connections",
    "inc_active_ws_connections",
    "dec_active_ws_connections",
    "set_celery_queue_depth",
    "get_metrics_payload",
    "CONTENT_TYPE_LATEST",
]
