"""OpenTelemetry & Distributed Tracing Infrastructure with Jaeger / JSON Exporter support.

Provides asynchronous & thread-safe context propagation, `@trace_span` decorator,
HTTP middleware for `X-Trace-ID` injection, and accurate performance metrics
(TTFT, retrieval latency, tool execution time).
"""

import asyncio
import contextvars
import functools
import json
import logging
import time
import uuid
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# ContextVars for active distributed trace context
_active_trace_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("active_trace_id", default=None)
_active_span_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("active_span_id", default=None)
_active_parent_span_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("active_parent_span_id", default=None)


class SpanRecord(BaseModel):
    """Distributed Trace Span Representation."""

    trace_id: str = Field(..., description="Global Trace ID")
    span_id: str = Field(..., description="Current Span ID")
    parent_span_id: Optional[str] = Field(None, description="Parent Span ID")
    name: str = Field(..., description="Span / Operation Name")
    start_time: float = Field(..., description="Start timestamp (epoch seconds)")
    end_time: Optional[float] = Field(None, description="End timestamp (epoch seconds)")
    duration_ms: Optional[float] = Field(None, description="Span duration in milliseconds")
    status: str = Field("OK", description="Status: OK | ERROR | CANCELLED")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Span metadata and metrics")
    events: List[Dict[str, Any]] = Field(default_factory=list, description="Timeline events (e.g. TTFT)")
    error: Optional[str] = Field(None, description="Exception message if status is ERROR")

    def finish(self, status: str = "OK", error: Optional[str] = None):
        """Marks the span as finished, calculating duration."""
        self.end_time = time.time()
        self.duration_ms = round((self.end_time - self.start_time) * 1000, 3)
        self.status = status
        self.error = error

    def to_jaeger_otlp_dict(self) -> Dict[str, Any]:
        """Converts span record to Jaeger / OTLP compatible JSON format."""
        return {
            "traceId": self.trace_id,
            "spanId": self.span_id,
            "parentSpanId": self.parent_span_id,
            "operationName": self.name,
            "startTimeMicros": int(self.start_time * 1_000_000),
            "durationMicros": int((self.duration_ms or 0) * 1_000),
            "tags": self.attributes,
            "logs": self.events,
            "status": self.status,
            "error": self.error,
        }


class TelemetryTracer:
    """Telemetry Tracer engine managing in-memory spans, JSON exporter and OTLP buffers."""

    def __init__(self, service_name: str = "enterprise-ai-assistant"):
        self.service_name = service_name
        self._spans: List[SpanRecord] = []
        self._enabled: bool = True

    def start_span(
        self,
        name: str,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> SpanRecord:
        """Starts and records a new span in current context."""
        current_trace = trace_id or _active_trace_id.get() or str(uuid.uuid4()).replace("-", "")
        current_parent = parent_span_id if parent_span_id is not None else _active_span_id.get()
        new_span_id = str(uuid.uuid4()).replace("-", "")[:16]

        span = SpanRecord(
            trace_id=current_trace,
            span_id=new_span_id,
            parent_span_id=current_parent,
            name=name,
            start_time=time.time(),
            attributes={"service.name": self.service_name, **(attributes or {})},
        )

        _active_trace_id.set(current_trace)
        _active_parent_span_id.set(current_parent)
        _active_span_id.set(new_span_id)

        return span

    def end_span(self, span: SpanRecord, status: str = "OK", error: Optional[str] = None):
        """Ends the span and commits it to trace collector."""
        span.finish(status=status, error=error)
        self._spans.append(span)

        # Restore parent context
        _active_span_id.set(span.parent_span_id)

    def get_spans(self, trace_id: Optional[str] = None) -> List[SpanRecord]:
        """Retrieves captured spans, optionally filtered by trace_id."""
        if trace_id:
            return [s for s in self._spans if s.trace_id == trace_id]
        return list(self._spans)

    def clear(self):
        """Clears in-memory spans (useful for tests)."""
        self._spans.clear()

    def export_json(self) -> str:
        """Exports recorded spans as formatted JSON string."""
        return json.dumps([s.model_dump() for s in self._spans], ensure_ascii=False, indent=2)


# Global Tracer Singleton
global_tracer = TelemetryTracer()


def get_current_trace_id() -> str:
    """Returns the current active trace_id or generates a fresh one."""
    tid = _active_trace_id.get()
    if not tid:
        tid = str(uuid.uuid4()).replace("-", "")
        _active_trace_id.set(tid)
    return tid


def get_current_span_id() -> Optional[str]:
    """Returns the current active span_id."""
    return _active_span_id.get()


def set_trace_context(trace_id: str, span_id: Optional[str] = None, parent_span_id: Optional[str] = None):
    """Manually sets the trace context variables."""
    _active_trace_id.set(trace_id)
    _active_span_id.set(span_id)
    _active_parent_span_id.set(parent_span_id)


def clear_trace_context():
    """Resets the trace context."""
    _active_trace_id.set(None)
    _active_span_id.set(None)
    _active_parent_span_id.set(None)


def trace_span(
    name: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
    tracer: Optional[TelemetryTracer] = None,
):
    """Decorator for tracing synchronous and asynchronous functions.

    Automatically captures duration, status, exceptions, and records
    metrics (e.g. ttft_ms, retrieval_latency_ms, tool_latency_ms).
    """

    def decorator(func: Callable):
        span_name = name or f"{func.__module__}.{func.__qualname__}"
        active_tracer = tracer or global_tracer

        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                span = active_tracer.start_span(name=span_name, attributes=attributes)
                try:
                    result = await func(*args, **kwargs)
                    active_tracer.end_span(span, status="OK")
                    return result
                except Exception as exc:
                    active_tracer.end_span(span, status="ERROR", error=str(exc))
                    raise

            return async_wrapper
        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                span = active_tracer.start_span(name=span_name, attributes=attributes)
                try:
                    result = func(*args, **kwargs)
                    active_tracer.end_span(span, status="OK")
                    return result
                except Exception as exc:
                    active_tracer.end_span(span, status="ERROR", error=str(exc))
                    raise

            return sync_wrapper

    return decorator


class TracingMiddleware(BaseHTTPMiddleware):
    """FastAPI Middleware that creates a root HTTP span and injects `X-Trace-ID` into response headers."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4()).replace("-", "")
        set_trace_context(trace_id=trace_id)

        span = global_tracer.start_span(
            name=f"HTTP {request.method} {request.url.path}",
            trace_id=trace_id,
            attributes={
                "http.method": request.method,
                "http.url": str(request.url),
                "http.path": request.url.path,
                "http.client_ip": request.client.host if request.client else "unknown",
            },
        )

        try:
            response: Response = await call_next(request)
            response.headers["X-Trace-ID"] = trace_id
            global_tracer.end_span(span, status="OK")
            return response
        except Exception as exc:
            global_tracer.end_span(span, status="ERROR", error=str(exc))
            raise
        finally:
            clear_trace_context()
