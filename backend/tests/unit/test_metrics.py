"""Unit tests for Prometheus Metrics Collection & /metrics endpoint.

Verifies:
1. Gauge, Counter, and Histogram metric collection and helper functions.
2. Label cardinality and observation correctness.
3. GET /metrics FastAPI endpoint formatting (text/plain Prometheus exposition format).
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.core.metrics import (
    llm_token_total,
    llm_time_to_first_token_seconds,
    prompt_cache_hits_total,
    prompt_cache_misses_total,
    active_websocket_connections,
    celery_queue_depth,
    record_llm_tokens,
    record_ttft,
    record_cache_hit,
    record_cache_miss,
    set_active_ws_connections,
    inc_active_ws_connections,
    dec_active_ws_connections,
    set_celery_queue_depth,
    get_metrics_payload,
)


@pytest.fixture
def client():
    return TestClient(app)


def test_llm_token_total_counter():
    """Test llm_token_total counter increments with labels."""
    initial_input = llm_token_total.labels(model="qwen-max", type="input")._value.get()
    initial_output = llm_token_total.labels(model="qwen-max", type="output")._value.get()

    record_llm_tokens("qwen-max", "input", 120)
    record_llm_tokens("qwen-max", "output", 85)

    assert llm_token_total.labels(model="qwen-max", type="input")._value.get() == initial_input + 120
    assert llm_token_total.labels(model="qwen-max", type="output")._value.get() == initial_output + 85


def test_llm_ttft_histogram():
    """Test llm_time_to_first_token_seconds histogram observation."""
    initial_sum = llm_time_to_first_token_seconds._sum.get()

    record_ttft(0.45)
    record_ttft(1.20)

    current_sum = llm_time_to_first_token_seconds._sum.get()
    assert current_sum >= initial_sum + 1.65

    # Verify through payload text
    payload = get_metrics_payload().decode("utf-8")
    assert "llm_time_to_first_token_seconds_bucket" in payload
    assert "llm_time_to_first_token_seconds_count" in payload
    assert "llm_time_to_first_token_seconds_sum" in payload


def test_prompt_cache_counters():
    """Test prompt cache hits and misses counters."""
    initial_hits = prompt_cache_hits_total._value.get()
    initial_misses = prompt_cache_misses_total._value.get()

    record_cache_hit(3)
    record_cache_miss(2)

    assert prompt_cache_hits_total._value.get() == initial_hits + 3
    assert prompt_cache_misses_total._value.get() == initial_misses + 2


def test_websocket_connections_gauge():
    """Test active_websocket_connections gauge manipulations."""
    set_active_ws_connections(10)
    assert active_websocket_connections._value.get() == 10

    inc_active_ws_connections()
    assert active_websocket_connections._value.get() == 11

    dec_active_ws_connections()
    assert active_websocket_connections._value.get() == 10


def test_celery_queue_depth_gauge():
    """Test celery_queue_depth gauge setter."""
    set_celery_queue_depth(42)
    assert celery_queue_depth._value.get() == 42


def test_get_metrics_payload():
    """Test raw metric payload generation."""
    payload = get_metrics_payload()
    assert isinstance(payload, bytes)
    text = payload.decode("utf-8")
    assert "llm_token_total" in text
    assert "llm_time_to_first_token_seconds" in text
    assert "prompt_cache_hits_total" in text
    assert "active_websocket_connections" in text
    assert "celery_queue_depth" in text


def test_metrics_api_endpoint(client):
    """Test GET /metrics endpoint returns 200 and Prometheus formatted text."""
    # Ensure some data exists
    record_llm_tokens("gpt-4o", "input", 50)
    record_ttft(0.35)
    set_active_ws_connections(5)
    set_celery_queue_depth(3)

    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers.get("content-type", "")

    body = response.text
    assert "# HELP llm_token_total" in body
    assert "# TYPE llm_token_total counter" in body
    assert 'llm_token_total{model="gpt-4o",type="input"}' in body
    assert "llm_time_to_first_token_seconds_bucket" in body
    assert "prompt_cache_hits_total" in body
    assert "active_websocket_connections 5.0" in body
    assert "celery_queue_depth 3.0" in body
