"""Prometheus Metrics Collector & Sanitized Tool Audit Buffer for Enterprise AI Digital Assistant.

Defines production-grade Prometheus metrics for LLM token usage, TTFT latency,
cache hits/misses, active WebSocket connections, Celery queue depth, and tool
execution telemetry/audits.
"""

from collections import deque
from datetime import datetime, timezone
import re
import threading
from typing import Any, Deque, Dict, List, Union
import uuid
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
    ["model", "type"],  # label 'type': 'input' or 'output'
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

# 6. Tool Execution Counters & Latency Histogram
tool_executions_total = Counter(
    "tool_executions_total",
    "Total number of business and RAG tool invocations",
    ["tool_name", "status"],  # label 'status': 'success' or 'error'
)

tool_execution_duration_seconds = Histogram(
    "tool_execution_duration_seconds",
    "Execution duration of registered tools in seconds",
    ["tool_name"],
    buckets=(0.005, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

# Thread-safe bounded ring buffer for sanitized recent tool execution audits
_TOOL_AUDIT_LOCK = threading.RLock()
_RECENT_TOOL_AUDITS: Deque[Dict[str, Any]] = deque(maxlen=200)
_SECRET_SNIPPET_RE = re.compile(r"(sk-[a-zA-Z0-9_\-]{10,}|Bearer\s+[a-zA-Z0-9_\-\.]{12,})", re.IGNORECASE)


def _sanitize_audit_summary(summary: str) -> str:
    """Redacts any credential-like pattern from audit summaries."""
    cleaned = (summary or "").strip()
    if not cleaned:
        return ""
    return _SECRET_SNIPPET_RE.sub("[REDACTED]", cleaned)[:180]


def estimate_token_count(text: str) -> int:
    """Estimates token count for mixed CJK and Latin text safely."""
    if not text:
        return 0
    cleaned = text.strip()
    if not cleaned:
        return 0
    cjk_chars = sum(1 for c in cleaned if "一" <= c <= "鿿")
    non_cjk_len = len(cleaned) - cjk_chars
    return max(1, cjk_chars + max(0, non_cjk_len // 4))


def record_llm_tokens(model: str, token_type: str, count: Union[int, float] = 1) -> None:
    """Record LLM token consumption by model and type (input/output)."""
    if count <= 0:
        return
    llm_token_total.labels(model=model, type=token_type).inc(count)


def record_ttft(seconds: float) -> None:
    """Record Time to First Token (TTFT) in seconds."""
    llm_time_to_first_token_seconds.observe(max(0.0, float(seconds)))


def record_cache_hit(count: int = 1) -> None:
    """Increment prompt cache hit counter."""
    prompt_cache_hits_total.inc(count)


def record_cache_miss(count: int = 1) -> None:
    """Increment prompt cache miss counter."""
    prompt_cache_misses_total.inc(count)


def set_active_ws_connections(count: int) -> None:
    """Set the number of active WebSocket connections."""
    active_websocket_connections.set(max(0, int(count)))


def inc_active_ws_connections() -> None:
    """Increment active WebSocket connections count by 1."""
    active_websocket_connections.inc()


def dec_active_ws_connections() -> None:
    """Decrement active WebSocket connections count by 1."""
    active_websocket_connections.dec()


def set_celery_queue_depth(depth: int) -> None:
    """Set current Celery queue depth."""
    celery_queue_depth.set(depth)


def record_tool_execution(
    tool_name: str,
    status: str,
    duration_seconds: float,
    summary: str = "",
) -> None:
    """Records tool invocation Prometheus counters/histogram and sanitized audit metadata."""
    normalized_status = "error" if str(status).lower() in ("error", "failed", "failure") else "success"
    elapsed = max(0.0, float(duration_seconds))

    tool_executions_total.labels(tool_name=tool_name, status=normalized_status).inc()
    tool_execution_duration_seconds.labels(tool_name=tool_name).observe(elapsed)

    audit_entry: Dict[str, Any] = {
        "audit_id": f"AUD-{uuid.uuid4().hex[:8].upper()}",
        "tool_name": tool_name,
        "status": normalized_status,
        "duration_ms": round(elapsed * 1000, 2),
        "summary": _sanitize_audit_summary(summary),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with _TOOL_AUDIT_LOCK:
        _RECENT_TOOL_AUDITS.append(audit_entry)


record_tool_audit = record_tool_execution


def get_recent_tool_audits(limit: int = 20) -> List[Dict[str, Any]]:
    """Returns newest-first list of sanitized recent tool execution audit entries."""
    safe_limit = max(1, min(int(limit), 100))
    with _TOOL_AUDIT_LOCK:
        items = list(_RECENT_TOOL_AUDITS)
    items.reverse()
    return items[:safe_limit]


def clear_tool_audits() -> None:
    """Clears in-memory tool execution audit entries (intended for unit test isolation)."""
    with _TOOL_AUDIT_LOCK:
        _RECENT_TOOL_AUDITS.clear()


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
    "tool_executions_total",
    "tool_execution_duration_seconds",
    "estimate_token_count",
    "record_llm_tokens",
    "record_ttft",
    "record_cache_hit",
    "record_cache_miss",
    "set_active_ws_connections",
    "inc_active_ws_connections",
    "dec_active_ws_connections",
    "set_celery_queue_depth",
    "record_tool_execution",
    "record_tool_audit",
    "get_recent_tool_audits",
    "clear_tool_audits",
    "get_metrics_payload",
    "CONTENT_TYPE_LATEST",
]
