"""Unit Tests for AI Infrastructure Gateway (Prompt Cache, Token Monitor & Fallback)."""

import asyncio
import pytest
from typing import Dict, Any, Optional

from backend.core.llm_infra import LLMGateway


class MockAsyncRedis:
    """In-memory Async Redis Mock for unit testing LLMGateway."""

    def __init__(self):
        self.store: Dict[str, Any] = {}
        self.hashes: Dict[str, Dict[str, Any]] = {}
        self.lists: Dict[str, list] = {}

    async def get(self, key: str) -> Optional[str]:
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        self.store[key] = value
        return True

    async def hincrby(self, name: str, key: str, amount: int = 1) -> int:
        if name not in self.hashes:
            self.hashes[name] = {}
        curr = int(self.hashes[name].get(key, 0))
        new_val = curr + amount
        self.hashes[name][key] = str(new_val)
        return new_val

    async def hincrbyfloat(self, name: str, key: str, amount: float = 1.0) -> float:
        if name not in self.hashes:
            self.hashes[name] = {}
        curr = float(self.hashes[name].get(key, 0.0))
        new_val = curr + amount
        self.hashes[name][key] = str(new_val)
        return new_val

    async def hgetall(self, name: str) -> Dict[bytes, bytes]:
        if name not in self.hashes:
            return {}
        return {
            k.encode("utf-8"): str(v).encode("utf-8")
            for k, v in self.hashes[name].items()
        }

    async def rpush(self, name: str, value: str) -> int:
        if name not in self.lists:
            self.lists[name] = []
        self.lists[name].append(value)
        return len(self.lists[name])


@pytest.fixture
def mock_redis():
    return MockAsyncRedis()


@pytest.fixture
def llm_gateway(mock_redis):
    return LLMGateway(
        redis_client=mock_redis,
        primary_model_name="vllm-primary",
        fallback_model_name="vllm-backup",
        default_timeout=1.0,
        cache_ttl=3600,
    )


def test_token_estimation_and_cost_calculation(llm_gateway):
    """Verifies token estimation heuristics and cost calculation."""
    text = "Hello world! 这是一个测试文本。"
    tokens = llm_gateway.estimate_tokens(text)
    assert tokens > 0

    cost = llm_gateway.calculate_cost(
        prompt_tokens=100,
        completion_tokens=200,
        model_name="vllm-primary"
    )
    # 100/1000 * 0.0015 + 200/1000 * 0.002 = 0.00015 + 0.0004 = 0.00055
    assert cost == 0.00055


@pytest.mark.asyncio
async def test_prompt_hash_cache_miss_and_hit(llm_gateway):
    """Verifies Prompt Hash Cache miss on first call and hit on second call."""
    prompt = "Explain quantum computing in simple terms."

    # 1. First invocation: Cache Miss
    res1 = await llm_gateway.generate_response(prompt, use_cache=True)
    assert res1["cached"] is False
    assert res1["model_used"] == "vllm-primary"
    assert res1["fallback_triggered"] is False
    assert "[Primary Model Response]" in res1["content"]

    # 2. Second invocation: Cache Hit
    res2 = await llm_gateway.generate_response(prompt, use_cache=True)
    assert res2["cached"] is True
    assert res2["cost"] == 0.0
    assert res2["content"] == res1["content"]


@pytest.mark.asyncio
async def test_primary_model_custom_function(llm_gateway):
    """Verifies custom primary model function execution."""
    async def custom_primary(p: str) -> str:
        return f"Custom Output for: {p}"

    result = await llm_gateway.generate_response(
        prompt="Tell me a joke",
        primary_func=custom_primary,
        use_cache=False,
    )
    assert result["cached"] is False
    assert result["fallback_triggered"] is False
    assert result["content"] == "Custom Output for: Tell me a joke"
    assert result["prompt_tokens"] > 0
    assert result["completion_tokens"] > 0


@pytest.mark.asyncio
async def test_model_fallback_on_primary_exception(llm_gateway):
    """Verifies fallback strategy triggered when primary model raises an exception."""
    async def failing_primary(p: str) -> str:
        raise ValueError("Primary LLM Service Unavailable (503)")

    async def working_fallback(p: str) -> str:
        return f"Fallback Output for: {p}"

    result = await llm_gateway.generate_response(
        prompt="Synthesize research data",
        primary_func=failing_primary,
        fallback_func=working_fallback,
        use_cache=False,
    )

    assert result["cached"] is False
    assert result["fallback_triggered"] is True
    assert result["model_used"] == "vllm-backup"
    assert "Primary LLM Service Unavailable" in result["primary_error"]
    assert result["content"] == "Fallback Output for: Synthesize research data"


@pytest.mark.asyncio
async def test_model_fallback_on_primary_timeout(llm_gateway):
    """Verifies fallback strategy triggered when primary model times out."""
    async def slow_primary(p: str) -> str:
        await asyncio.sleep(2.0)
        return "Slow Primary Answer"

    async def fast_fallback(p: str) -> str:
        return "Fast Fallback Answer"

    result = await llm_gateway.generate_response(
        prompt="Generate real-time analytics",
        primary_func=slow_primary,
        fallback_func=fast_fallback,
        timeout=0.1,  # 100ms timeout to trigger fast timeout
        use_cache=False,
    )

    assert result["cached"] is False
    assert result["fallback_triggered"] is True
    assert result["model_used"] == "vllm-backup"
    assert result["content"] == "Fast Fallback Answer"


@pytest.mark.asyncio
async def test_token_stats_recording_and_retrieval(llm_gateway):
    """Verifies token metrics and cost recording in Redis stats."""
    await llm_gateway.generate_response("Query 1", use_cache=False)
    await llm_gateway.generate_response("Query 2", use_cache=False)

    stats = await llm_gateway.get_token_stats()
    assert stats["total_calls"] == 2
    assert stats["total_prompt_tokens"] > 0
    assert stats["total_completion_tokens"] > 0
    assert stats["total_tokens"] == stats["total_prompt_tokens"] + stats["total_completion_tokens"]
    assert stats["total_cost"] > 0.0
