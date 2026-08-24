"""Unit tests for OpenTelemetry & Jaeger Distributed Tracing Infrastructure (Issue-0024)."""

import asyncio
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.core.telemetry import (
    SpanRecord,
    TelemetryTracer,
    TracingMiddleware,
    clear_trace_context,
    get_current_span_id,
    get_current_trace_id,
    global_tracer,
    trace_span,
)


@pytest.fixture(autouse=True)
def clean_tracing_state():
    """Cleans global and local tracer state before each test."""
    clear_trace_context()
    global_tracer.clear()
    yield
    clear_trace_context()
    global_tracer.clear()


def test_span_record_lifecycle_and_otlp_dict():
    """Test SpanRecord initialization, finish duration calculation, and OTLP format export."""
    span = SpanRecord(
        trace_id="trace_123456",
        span_id="span_abcdef",
        name="test.operation",
        start_time=100.0,
        attributes={"user_id": "u001"},
    )
    assert span.status == "OK"
    assert span.duration_ms is None

    span.finish(status="OK")
    assert span.end_time is not None
    assert span.duration_ms >= 0

    otlp_data = span.to_jaeger_otlp_dict()
    assert otlp_data["traceId"] == "trace_123456"
    assert otlp_data["spanId"] == "span_abcdef"
    assert otlp_data["operationName"] == "test.operation"
    assert otlp_data["tags"]["user_id"] == "u001"


def test_tracer_nested_spans_and_context_propagation():
    """Test TelemetryTracer nested spans correctly propagate parent_span_id and maintain active context."""
    tracer = TelemetryTracer(service_name="test-service")

    # Root span
    root_span = tracer.start_span("root.operation", trace_id="trace_root_001")
    assert get_current_trace_id() == "trace_root_001"
    assert get_current_span_id() == root_span.span_id

    # Child span
    child_span = tracer.start_span("child.operation")
    assert child_span.parent_span_id == root_span.span_id
    assert child_span.trace_id == "trace_root_001"
    assert get_current_span_id() == child_span.span_id

    tracer.end_span(child_span, status="OK")
    assert get_current_span_id() == root_span.span_id

    tracer.end_span(root_span, status="OK")
    spans = tracer.get_spans(trace_id="trace_root_001")
    assert len(spans) == 2


def test_sync_trace_span_decorator():
    """Test @trace_span on synchronous function with execution metrics."""

    @trace_span(name="sync.calc", attributes={"step": "math"})
    def compute(a: int, b: int) -> int:
        return a + b

    res = compute(10, 20)
    assert res == 30

    spans = global_tracer.get_spans()
    assert len(spans) == 1
    assert spans[0].name == "sync.calc"
    assert spans[0].attributes["step"] == "math"
    assert spans[0].duration_ms >= 0


@pytest.mark.asyncio
async def test_async_trace_span_decorator_and_exception_capture():
    """Test @trace_span on async coroutines and verifying exception capture with status=ERROR."""

    @trace_span(name="async.fetch_knowledge")
    async def async_fetch():
        await asyncio.sleep(0.01)
        return {"data": "ok"}

    @trace_span(name="async.failing_node")
    async def async_fail():
        raise ValueError("Simulated pipeline failure")

    # Successful call
    res = await async_fetch()
    assert res["data"] == "ok"

    # Failing call
    with pytest.raises(ValueError, match="Simulated pipeline failure"):
        await async_fail()

    spans = global_tracer.get_spans()
    assert len(spans) == 2

    fail_span = next(s for s in spans if s.name == "async.failing_node")
    assert fail_span.status == "ERROR"
    assert "Simulated pipeline failure" in fail_span.error


def test_tracing_middleware_x_trace_id_injection():
    """Test FastAPI TracingMiddleware creates root span and injects X-Trace-ID response header."""
    app = FastAPI()
    app.add_middleware(TracingMiddleware)

    @app.get("/api/test/ping")
    def ping():
        return {"msg": "pong", "trace_id": get_current_trace_id()}

    client = TestClient(app)

    # 1. Without incoming X-Trace-ID (auto-generate)
    resp1 = client.get("/api/test/ping")
    assert resp1.status_code == 200
    assert "X-Trace-ID" in resp1.headers
    generated_tid = resp1.headers["X-Trace-ID"]
    assert len(generated_tid) >= 16

    # 2. With client-provided X-Trace-ID (pass-through propagation)
    custom_tid = "custom-trace-uuid-999"
    resp2 = client.get("/api/test/ping", headers={"X-Trace-ID": custom_tid})
    assert resp2.status_code == 200
    assert resp2.headers["X-Trace-ID"] == custom_tid


def test_telemetry_json_export():
    """Test TelemetryTracer export_json produces valid JSON string."""
    span = global_tracer.start_span("json.test.span")
    global_tracer.end_span(span)

    exported = global_tracer.export_json()
    assert "json.test.span" in exported
    assert "trace_id" in exported
