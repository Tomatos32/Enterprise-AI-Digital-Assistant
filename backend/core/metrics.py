"""Prometheus Metrics Collector & Sanitized Tool Audit Buffer for Enterprise AI Digital Assistant.

Defines production-grade Prometheus metrics for LLM token usage, TTFT latency,
cache hits/misses, active WebSocket connections, Celery queue depth, and tool
execution telemetry/audits.
"""

from collections import deque
from datetime import datetime, timezone
import math
import re
import threading
from typing import Any, Deque, Dict, List, Optional, Sequence, Tuple, Union
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


# ---------------------------------------------------------------------------
# Thread-Safe Cognitive Pipeline Telemetry Aggregators (Routing / Rewriting / Slots)
# ---------------------------------------------------------------------------

_COGNITIVE_LOCK = threading.RLock()

_INTENT_LABELS: List[Tuple[str, str]] = [
    ("retrieve", "制度检索"),
    ("tool", "工具执行"),
    ("approval", "审批流转"),
    ("chat", "常规对话"),
]

_TIER_LABELS: List[Tuple[str, str]] = [
    ("tier_0_override", "显式覆盖与结构化调用"),
    ("tier_1_directive", "确定性指令/数据源"),
    ("tier_1_guard", "确定性规则护栏"),
    ("tier_2_llm", "轻量认知分类器"),
    ("tier_3_fallback", "多轮规则降级兜底"),
]

_DEFAULT_DOMAINS: Tuple[str, ...] = ("IT", "HR", "FINANCE", "ADMIN")

_ROUTING_STATS: Dict[str, Any] = {
    "total_routed": 0,
    "compound_count": 0,
    "llm_fallback_count": 0,
    "by_intent": {k: 0 for k, _ in _INTENT_LABELS},
    "by_tier": {k: 0 for k, _ in _TIER_LABELS},
}
_RECENT_ROUTING_DECISIONS: Deque[Dict[str, Any]] = deque(maxlen=100)

_REWRITE_STATS: Dict[str, Any] = {
    "total_rewrites": 0,
    "llm_rewrite_count": 0,
    "deterministic_count": 0,
    "coreference_resolved_count": 0,
    "fallback_count": 0,
    "total_latency_ms": 0.0,
    "by_domain": {d: 0 for d in _DEFAULT_DOMAINS},
}
_RECENT_REWRITE_SAMPLES: Deque[Dict[str, Any]] = deque(maxlen=100)

_SLOT_STATS: Dict[str, int] = {
    "total_extractions": 0,
    "complete_count": 0,
    "clarification_count": 0,
    "hybrid_llm_count": 0,
    "multi_turn_merge_count": 0,
}


def _sanitize_cognitive_text(text: str, max_len: int = 160) -> str:
    """Sanitizes credential patterns and truncates text to <= max_len characters."""
    return _sanitize_audit_summary(text)[:max_len]


def record_routing_event(
    *,
    intent: str,
    tier: str,
    routing_method: str,
    confidence: float = 0.0,
    secondary_intent: str = "",
    fallback_triggered: bool = False,
) -> None:
    """Records a cognitive intent routing decision into thread-safe memory counters and ring buffer."""
    norm_intent = (intent or "chat").strip().lower()
    norm_tier = (tier or "tier_1_guard").strip().lower()
    norm_secondary = (secondary_intent or "").strip().lower()
    norm_method = _sanitize_cognitive_text(routing_method or "unknown", max_len=64)
    raw_conf = float(confidence)
    safe_conf = round(max(0.0, min(1.0, raw_conf if math.isfinite(raw_conf) else 0.0)), 3)

    entry: Dict[str, Any] = {
        "decision_id": f"RTE-{uuid.uuid4().hex[:8].upper()}",
        "intent": norm_intent,
        "secondary_intent": norm_secondary,
        "routing_method": norm_method,
        "tier": norm_tier,
        "confidence": safe_conf,
        "fallback_triggered": bool(fallback_triggered),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    with _COGNITIVE_LOCK:
        _ROUTING_STATS["total_routed"] += 1
        if norm_secondary:
            _ROUTING_STATS["compound_count"] += 1
        if fallback_triggered:
            _ROUTING_STATS["llm_fallback_count"] += 1
        _ROUTING_STATS["by_intent"][norm_intent] = _ROUTING_STATS["by_intent"].get(norm_intent, 0) + 1
        _ROUTING_STATS["by_tier"][norm_tier] = _ROUTING_STATS["by_tier"].get(norm_tier, 0) + 1
        _RECENT_ROUTING_DECISIONS.append(entry)


def record_rewrite_event(
    *,
    original_query: str,
    standalone_query: str,
    sub_queries: Optional[Sequence[str]] = None,
    domains: Optional[Sequence[str]] = None,
    rewrite_method: str = "deterministic",
    coreference_resolved: bool = False,
    fallback_triggered: bool = False,
    latency_ms: float = 0.0,
) -> None:
    """Records a query rewriting diagnostic sample into thread-safe memory counters and ring buffer."""
    norm_method = (rewrite_method or "deterministic").strip().lower()
    raw_latency = float(latency_ms)
    safe_latency = round(max(0.0, raw_latency if math.isfinite(raw_latency) else 0.0), 2)
    safe_domains = [
        str(d).strip().upper()
        for d in (domains or [])
        if str(d).strip()
    ][:6]
    safe_sub_queries = [
        _sanitize_cognitive_text(str(sq), max_len=160)
        for sq in (sub_queries or [])
        if str(sq).strip()
    ][:6]

    sample: Dict[str, Any] = {
        "rewrite_id": f"RWT-{uuid.uuid4().hex[:8].upper()}",
        "original_query": _sanitize_cognitive_text(original_query, max_len=160),
        "standalone_query": _sanitize_cognitive_text(standalone_query, max_len=160),
        "sub_queries": safe_sub_queries,
        "domains": safe_domains,
        "rewrite_method": norm_method,
        "coreference_resolved": bool(coreference_resolved),
        "fallback_triggered": bool(fallback_triggered),
        "latency_ms": safe_latency,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    with _COGNITIVE_LOCK:
        _REWRITE_STATS["total_rewrites"] += 1
        if norm_method in ("llm", "llm_rewrite"):
            _REWRITE_STATS["llm_rewrite_count"] += 1
        else:
            _REWRITE_STATS["deterministic_count"] += 1
        if coreference_resolved:
            _REWRITE_STATS["coreference_resolved_count"] += 1
        if fallback_triggered:
            _REWRITE_STATS["fallback_count"] += 1
        _REWRITE_STATS["total_latency_ms"] += safe_latency
        for dom in safe_domains:
            _REWRITE_STATS["by_domain"][dom] = _REWRITE_STATS["by_domain"].get(dom, 0) + 1
        _RECENT_REWRITE_SAMPLES.append(sample)


def record_slot_extraction_event(
    *,
    is_complete: bool,
    extraction_method: str = "deterministic",
    merged_from_history: bool = False,
) -> None:
    """Records a semantic slot extraction outcome into thread-safe counters."""
    norm_method = (extraction_method or "deterministic").strip().lower()
    with _COGNITIVE_LOCK:
        _SLOT_STATS["total_extractions"] += 1
        if is_complete:
            _SLOT_STATS["complete_count"] += 1
        else:
            _SLOT_STATS["clarification_count"] += 1
        if norm_method == "hybrid_llm":
            _SLOT_STATS["hybrid_llm_count"] += 1
        if merged_from_history:
            _SLOT_STATS["multi_turn_merge_count"] += 1


def get_cognitive_telemetry_snapshot(limit: int = 20) -> Dict[str, Any]:
    """Returns a thread-safe snapshot of routing, rewriting, and slot extraction telemetry."""
    safe_limit = max(1, min(int(limit), 100))
    with _COGNITIVE_LOCK:
        total_routed = int(_ROUTING_STATS["total_routed"])
        intent_counts: Dict[str, int] = dict(_ROUTING_STATS["by_intent"])
        tier_counts: Dict[str, int] = dict(_ROUTING_STATS["by_tier"])

        by_intent: List[Dict[str, Any]] = []
        seen_intents = set()
        for code, label in _INTENT_LABELS:
            cnt = int(intent_counts.get(code, 0))
            share = round((cnt / total_routed) * 100.0, 1) if total_routed > 0 else 0.0
            by_intent.append({"intent": code, "label": label, "count": cnt, "share_percent": share})
            seen_intents.add(code)
        for code, cnt in intent_counts.items():
            if code not in seen_intents and cnt > 0:
                share = round((cnt / total_routed) * 100.0, 1) if total_routed > 0 else 0.0
                by_intent.append({"intent": code, "label": code, "count": int(cnt), "share_percent": share})

        by_tier: List[Dict[str, Any]] = []
        seen_tiers = set()
        for code, label in _TIER_LABELS:
            cnt = int(tier_counts.get(code, 0))
            share = round((cnt / total_routed) * 100.0, 1) if total_routed > 0 else 0.0
            by_tier.append({"tier": code, "label": label, "count": cnt, "share_percent": share})
            seen_tiers.add(code)
        for code, cnt in tier_counts.items():
            if code not in seen_tiers and cnt > 0:
                share = round((cnt / total_routed) * 100.0, 1) if total_routed > 0 else 0.0
                by_tier.append({"tier": code, "label": code, "count": int(cnt), "share_percent": share})

        recent_decisions = list(_RECENT_ROUTING_DECISIONS)
        recent_decisions.reverse()

        total_rewrites = int(_REWRITE_STATS["total_rewrites"])
        avg_latency = (
            round(float(_REWRITE_STATS["total_latency_ms"]) / total_rewrites, 2)
            if total_rewrites > 0
            else 0.0
        )
        domain_counts: Dict[str, int] = dict(_REWRITE_STATS["by_domain"])
        by_domain: List[Dict[str, Any]] = []
        seen_domains = set()
        for dom in _DEFAULT_DOMAINS:
            by_domain.append({"domain": dom, "count": int(domain_counts.get(dom, 0))})
            seen_domains.add(dom)
        for dom, cnt in sorted(domain_counts.items()):
            if dom not in seen_domains and cnt > 0:
                by_domain.append({"domain": dom, "count": int(cnt)})

        recent_samples = list(_RECENT_REWRITE_SAMPLES)
        recent_samples.reverse()

        return {
            "routing": {
                "total_routed": total_routed,
                "compound_count": int(_ROUTING_STATS["compound_count"]),
                "llm_fallback_count": int(_ROUTING_STATS["llm_fallback_count"]),
                "by_intent": by_intent,
                "by_tier": by_tier,
                "recent_decisions": recent_decisions[:safe_limit],
            },
            "rewriting": {
                "total_rewrites": total_rewrites,
                "llm_rewrite_count": int(_REWRITE_STATS["llm_rewrite_count"]),
                "deterministic_count": int(_REWRITE_STATS["deterministic_count"]),
                "coreference_resolved_count": int(_REWRITE_STATS["coreference_resolved_count"]),
                "fallback_count": int(_REWRITE_STATS["fallback_count"]),
                "avg_latency_ms": avg_latency,
                "by_domain": by_domain,
                "recent_samples": recent_samples[:safe_limit],
            },
            "slots": {
                "total_extractions": int(_SLOT_STATS["total_extractions"]),
                "complete_count": int(_SLOT_STATS["complete_count"]),
                "clarification_count": int(_SLOT_STATS["clarification_count"]),
                "hybrid_llm_count": int(_SLOT_STATS["hybrid_llm_count"]),
                "multi_turn_merge_count": int(_SLOT_STATS["multi_turn_merge_count"]),
            },
        }


def clear_cognitive_telemetry() -> None:
    """Resets in-memory cognitive routing, rewriting, and slot extraction telemetry (for test isolation)."""
    with _COGNITIVE_LOCK:
        _ROUTING_STATS["total_routed"] = 0
        _ROUTING_STATS["compound_count"] = 0
        _ROUTING_STATS["llm_fallback_count"] = 0
        _ROUTING_STATS["by_intent"] = {k: 0 for k, _ in _INTENT_LABELS}
        _ROUTING_STATS["by_tier"] = {k: 0 for k, _ in _TIER_LABELS}
        _RECENT_ROUTING_DECISIONS.clear()

        _REWRITE_STATS["total_rewrites"] = 0
        _REWRITE_STATS["llm_rewrite_count"] = 0
        _REWRITE_STATS["deterministic_count"] = 0
        _REWRITE_STATS["coreference_resolved_count"] = 0
        _REWRITE_STATS["fallback_count"] = 0
        _REWRITE_STATS["total_latency_ms"] = 0.0
        _REWRITE_STATS["by_domain"] = {d: 0 for d in _DEFAULT_DOMAINS}
        _RECENT_REWRITE_SAMPLES.clear()

        _SLOT_STATS["total_extractions"] = 0
        _SLOT_STATS["complete_count"] = 0
        _SLOT_STATS["clarification_count"] = 0
        _SLOT_STATS["hybrid_llm_count"] = 0
        _SLOT_STATS["multi_turn_merge_count"] = 0


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
    "record_routing_event",
    "record_rewrite_event",
    "record_slot_extraction_event",
    "get_cognitive_telemetry_snapshot",
    "clear_cognitive_telemetry",
    "get_metrics_payload",
    "CONTENT_TYPE_LATEST",
]
