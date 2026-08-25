"""Unit tests for LLMGateway and ABTestingGateway (Issue-0029 - Sprint 22)."""

import asyncio
import pytest
from unittest.mock import AsyncMock
from backend.core.llm_gateway import LLMGateway, ABTestingGateway, LLMResponse


@pytest.mark.asyncio
async def test_llm_gateway_prompt_caching():
    """Test LLMGateway prompt hash caching mechanism."""
    gateway = LLMGateway(primary_model="gpt-4o", enable_cache=True)
    prompt = "What is the reimbursement limit for team meals?"

    # First call (Cache Miss)
    resp1 = await gateway.invoke(prompt=prompt)
    assert isinstance(resp1, LLMResponse)
    assert resp1.cached is False
    assert "gpt-4o" in resp1.model_used

    # Second call with same prompt (Cache Hit)
    resp2 = await gateway.invoke(prompt=prompt)
    assert resp2.cached is True
    assert resp2.content == resp1.content
    assert resp2.tokens_used == 0


@pytest.mark.asyncio
async def test_llm_gateway_model_fallback():
    """Test LLMGateway fallback to secondary model when primary fails."""
    gateway = LLMGateway(primary_model="primary-failing-model", fallback_models=["backup-healthy-model"])

    async def mock_caller(model: str, prompt: str, system_prompt=None):
        if "failing" in model:
            raise RuntimeError("Primary model rate limit exceeded 429")
        return f"Backup reply from {model}"

    resp = await gateway.invoke(prompt="test prompt", llm_caller=mock_caller)
    assert resp.model_used == "backup-healthy-model"
    assert "Backup reply from backup-healthy-model" in resp.content


def test_ab_testing_deterministic_user_hashing():
    """Test deterministic user hash routing consistency and ratio balance."""
    gateway = ABTestingGateway(
        model_a="model-a",
        model_b="model-b",
        split_ratio_a=0.80,  # 80% to A, 20% to B
    )

    # 1. Determinism: Same user always gets the same group
    model1, group1 = gateway.route_user(user_id="user_10086")
    model2, group2 = gateway.route_user(user_id="user_10086")
    assert model1 == model2
    assert group1 == group2

    # 2. Ratio balance across large synthetic sample
    sample_size = 1000
    group_a_count = 0
    for i in range(sample_size):
        _, group = gateway.route_user(user_id=f"emp_{i:04d}")
        if group == "model_a":
            group_a_count += 1

    ratio_a = group_a_count / sample_size
    # Expect ~80% with +-5% margin
    assert 0.75 <= ratio_a <= 0.85


@pytest.mark.asyncio
async def test_ab_testing_shadow_mode_non_blocking():
    """Test Shadow Mode: synchronous return of primary while background shadow executes."""
    gateway = ABTestingGateway(
        model_a="model-primary",
        model_b="model-shadow-candidate",
        split_ratio_a=1.0,  # Force all users to Model A
        enable_shadow_mode=True,
        shadow_models=["model-shadow-candidate"],
    )

    called_shadow = asyncio.Event()

    async def tracking_caller(model: str, prompt: str, system_prompt=None):
        if model == "model-shadow-candidate":
            await asyncio.sleep(0.02)
            called_shadow.set()
            return "Shadow model generated response"
        return "Primary model generated response"

    # Invoke primary
    resp = await gateway.invoke(
        user_id="user_test_01",
        prompt="Explain company leave policy",
        llm_caller=tracking_caller,
    )

    # Primary returns immediately
    assert resp.model_used == "model-primary"
    assert resp.content == "Primary model generated response"
    assert resp.group == "model_a"

    # Wait for shadow background execution
    await asyncio.wait_for(called_shadow.wait(), timeout=1.0)
    # Wait small tick for stats update
    await asyncio.sleep(0.05)

    metrics = gateway.get_comparison_metrics()
    assert metrics["model_a"]["requests"] == 1
    assert metrics["shadow"]["requests"] == 1


@pytest.mark.asyncio
async def test_ab_testing_metrics_and_feedback():
    """Test comparative metrics aggregation with positive/negative feedback."""
    mock_redis = AsyncMock()
    gateway = ABTestingGateway(
        model_a="model-a",
        model_b="model-b",
        split_ratio_a=0.5,
        redis_client=mock_redis,
    )

    # Simulate calls
    await gateway.invoke(user_id="u1", prompt="p1")
    await gateway.invoke(user_id="u2", prompt="p2")

    # Record feedback
    await gateway.record_feedback(group="model_a", is_positive=True)
    await gateway.record_feedback(group="model_a", is_positive=True)
    await gateway.record_feedback(group="model_a", is_positive=False)
    await gateway.record_feedback(group="model_b", is_positive=True)

    metrics = gateway.get_comparison_metrics()
    assert "model_a" in metrics
    assert "model_b" in metrics
    assert metrics["model_a"]["positive_feedback"] == 2
    assert metrics["model_a"]["negative_feedback"] == 1
    assert metrics["model_a"]["satisfaction_rate"] == round(2 / 3, 4)
    assert metrics["model_b"]["satisfaction_rate"] == 1.0
