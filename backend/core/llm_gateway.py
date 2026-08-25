"""LLM Gateway with Prompt Caching, Token Monitoring, Model Fallback, and A/B Testing & Shadow Deployment."""

import asyncio
import hashlib
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class LLMResponse(BaseModel):
    """Unified LLM Response object."""
    content: str
    model_used: str
    tokens_used: int = 0
    latency: float = 0.0
    cached: bool = False
    is_shadow: bool = False
    group: Optional[str] = None  # 'control' (A), 'candidate' (B), 'shadow', etc.
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LLMGateway:
    """Production LLM Gateway supporting Prompt Hash Caching, Token Monitoring, and Model Fallback."""

    def __init__(
        self,
        primary_model: str = "gpt-4o",
        fallback_models: Optional[List[str]] = None,
        cache_ttl_seconds: int = 3600,
        enable_cache: bool = True,
    ):
        self.primary_model = primary_model
        self.fallback_models = fallback_models or ["claude-3-5-sonnet", "qwen-max"]
        self.cache_ttl_seconds = cache_ttl_seconds
        self.enable_cache = enable_cache
        self._memory_cache: Dict[str, Tuple[str, float]] = {}  # hash -> (content, timestamp)
        self.total_tokens_consumed: int = 0

    def compute_prompt_hash(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Compute SHA256 hash for prompt caching."""
        full_text = f"{system_prompt or ''}::{prompt}".encode("utf-8")
        return hashlib.sha256(full_text).hexdigest()

    async def invoke(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        llm_caller: Optional[Callable[..., Any]] = None,
    ) -> LLMResponse:
        """Invoke primary model with fallback and caching."""
        cache_key = self.compute_prompt_hash(prompt, system_prompt)

        # 1. Check Cache
        if self.enable_cache and cache_key in self._memory_cache:
            content, ts = self._memory_cache[cache_key]
            if time.time() - ts <= self.cache_ttl_seconds:
                return LLMResponse(
                    content=content,
                    model_used=self.primary_model,
                    tokens_used=0,
                    latency=0.001,
                    cached=True,
                )

        # 2. Try Primary Model then Fallbacks
        candidate_models = [self.primary_model] + self.fallback_models
        last_error = None

        for model in candidate_models:
            start_time = time.time()
            try:
                if llm_caller:
                    content = await llm_caller(model=model, prompt=prompt, system_prompt=system_prompt)
                else:
                    # Simulated execution for offline testing
                    await asyncio.sleep(0.01)
                    content = f"Response from {model} for: {prompt[:30]}"

                latency = round(time.time() - start_time, 4)
                tokens = len(prompt.split()) + len(content.split())
                self.total_tokens_consumed += tokens

                # Save cache
                if self.enable_cache:
                    self._memory_cache[cache_key] = (content, time.time())

                return LLMResponse(
                    content=content,
                    model_used=model,
                    tokens_used=tokens,
                    latency=latency,
                    cached=False,
                )
            except Exception as e:
                logger.warning("Model %s failed: %s. Trying fallback...", model, str(e))
                last_error = e
                continue

        raise RuntimeError(f"All candidate LLM models failed. Last error: {last_error}")


class ABTestingGateway:
    """A/B Testing & Shadow Deployment Gateway for Enterprise AI Models.

    Features:
    - User ID deterministic hashing for consistent traffic routing (e.g. Model-A: 90%, Model-B: 10%).
    - Shadow Deployment Mode: Synchronously returns primary model output while asynchronously
      dispatching candidate models in the background without blocking the user.
    - Performance & feedback metric tracking saved in Redis / local memory stats.
    """

    def __init__(
        self,
        model_a: str = "model-primary-v1",
        model_b: str = "model-candidate-v2",
        split_ratio_a: float = 0.90,  # 90% traffic to Model A, 10% to Model B
        enable_shadow_mode: bool = False,
        shadow_models: Optional[List[str]] = None,
        redis_client: Optional[Any] = None,
    ):
        if not (0.0 <= split_ratio_a <= 1.0):
            raise ValueError("split_ratio_a must be between 0.0 and 1.0")

        self.model_a = model_a
        self.model_b = model_b
        self.split_ratio_a = split_ratio_a
        self.enable_shadow_mode = enable_shadow_mode
        self.shadow_models = shadow_models or ([model_b] if enable_shadow_mode else [])
        self.redis_client = redis_client

        # Local stats repository for standalone / in-memory operation
        self.metrics_repo: Dict[str, Dict[str, Any]] = {
            "model_a": {"requests": 0, "total_latency": 0.0, "positive_feedback": 0, "negative_feedback": 0},
            "model_b": {"requests": 0, "total_latency": 0.0, "positive_feedback": 0, "negative_feedback": 0},
            "shadow": {"requests": 0, "total_latency": 0.0, "positive_feedback": 0, "negative_feedback": 0},
        }

    def compute_user_hash_ratio(self, user_id: Union[str, int]) -> float:
        """Compute a deterministic float in [0.0, 1.0) based on user_id MD5 hash."""
        uid_str = str(user_id).strip()
        hash_val = hashlib.md5(uid_str.encode("utf-8")).hexdigest()
        # Take first 8 hex characters (32 bits) and normalize to [0.0, 1.0)
        integer_val = int(hash_val[:8], 16)
        return integer_val / 0xFFFFFFFF

    def route_user(self, user_id: Union[str, int]) -> Tuple[str, str]:
        """Determine which model and group a user should be routed to.

        Returns:
            Tuple[model_name, group_name ('model_a' | 'model_b')]
        """
        ratio = self.compute_user_hash_ratio(user_id)
        if ratio < self.split_ratio_a:
            return self.model_a, "model_a"
        else:
            return self.model_b, "model_b"

    async def _execute_model_call(
        self,
        model: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        llm_caller: Optional[Callable[..., Any]] = None,
    ) -> Tuple[str, float, int]:
        """Execute a model call and return (content, latency, token_count)."""
        start = time.time()
        if llm_caller:
            content = await llm_caller(model=model, prompt=prompt, system_prompt=system_prompt)
        else:
            await asyncio.sleep(0.01)
            content = f"[{model}] response to: {prompt[:30]}"
        latency = round(time.time() - start, 4)
        tokens = len(prompt.split()) + len(str(content).split())
        return str(content), latency, tokens

    async def _record_metric(
        self,
        group: str,
        model: str,
        latency: float,
        is_shadow: bool = False,
    ):
        """Record request and latency metrics into memory and Redis."""
        key = "shadow" if is_shadow else group
        if key in self.metrics_repo:
            self.metrics_repo[key]["requests"] += 1
            self.metrics_repo[key]["total_latency"] += latency

        # Optional Redis telemetry persistence
        if self.redis_client:
            try:
                redis_key = f"metrics:ab_test:{key}"
                if hasattr(self.redis_client, "hincrby"):
                    await self.redis_client.hincrby(redis_key, "requests", 1)
                    await self.redis_client.hincrbyfloat(redis_key, "total_latency", latency)
            except Exception as e:
                logger.debug("Redis metric recording failed (ignoring in fallback mode): %s", e)

    async def _dispatch_shadow_call(
        self,
        model: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        llm_caller: Optional[Callable[..., Any]] = None,
    ):
        """Background asynchronous shadow model execution."""
        try:
            content, latency, tokens = await self._execute_model_call(
                model=model,
                prompt=prompt,
                system_prompt=system_prompt,
                llm_caller=llm_caller,
            )
            await self._record_metric(group="shadow", model=model, latency=latency, is_shadow=True)
            logger.info("Shadow model %s executed successfully in background. Latency: %.4fs", model, latency)
        except Exception as e:
            logger.warning("Shadow model %s execution failed in background: %s", model, e)

    async def invoke(
        self,
        user_id: Union[str, int],
        prompt: str,
        system_prompt: Optional[str] = None,
        llm_caller: Optional[Callable[..., Any]] = None,
    ) -> LLMResponse:
        """Route user to target model in A/B test and optionally trigger shadow execution."""
        # 1. Routing decision
        routed_model, group = self.route_user(user_id)

        # 2. Main synchronous call
        content, latency, tokens = await self._execute_model_call(
            model=routed_model,
            prompt=prompt,
            system_prompt=system_prompt,
            llm_caller=llm_caller,
        )

        # 3. Record primary metric
        await self._record_metric(group=group, model=routed_model, latency=latency, is_shadow=False)

        # 4. Trigger Shadow Dispatch if enabled (non-blocking)
        if self.enable_shadow_mode:
            for shadow_model in self.shadow_models:
                if shadow_model != routed_model:
                    asyncio.create_task(
                        self._dispatch_shadow_call(
                            model=shadow_model,
                            prompt=prompt,
                            system_prompt=system_prompt,
                            llm_caller=llm_caller,
                        )
                    )

        return LLMResponse(
            content=content,
            model_used=routed_model,
            tokens_used=tokens,
            latency=latency,
            cached=False,
            is_shadow=False,
            group=group,
            metadata={"user_id": str(user_id), "routed_group": group},
        )

    async def record_feedback(self, group: str, is_positive: bool):
        """Record user feedback (thumbs up / down) for A/B comparison."""
        key = group if group in self.metrics_repo else "model_a"
        if is_positive:
            self.metrics_repo[key]["positive_feedback"] += 1
        else:
            self.metrics_repo[key]["negative_feedback"] += 1

        if self.redis_client:
            try:
                field = "positive_feedback" if is_positive else "negative_feedback"
                await self.redis_client.hincrby(f"metrics:ab_test:{key}", field, 1)
            except Exception as e:
                logger.debug("Redis feedback recording failed: %s", e)

    def get_comparison_metrics(self) -> Dict[str, Any]:
        """Get formatted comparative metrics for Model A vs Model B vs Shadow."""
        summary = {}
        for group, data in self.metrics_repo.items():
            reqs = data["requests"]
            avg_latency = round(data["total_latency"] / reqs, 4) if reqs > 0 else 0.0
            pos = data["positive_feedback"]
            neg = data["negative_feedback"]
            total_fb = pos + neg
            satisfaction = round(pos / total_fb, 4) if total_fb > 0 else 0.0

            summary[group] = {
                "requests": reqs,
                "avg_latency_seconds": avg_latency,
                "positive_feedback": pos,
                "negative_feedback": neg,
                "satisfaction_rate": satisfaction,
            }
        return summary
