"""AI Infrastructure Gateway: Prompt Cache, Token Monitor, and Fallback Strategy."""

import json
import logging
import hashlib
import asyncio
from typing import Dict, Any, Callable, Awaitable, Optional

import redis.asyncio as aioredis
from backend.core.redis import get_redis_client

logger = logging.getLogger(__name__)


class LLMGateway:
    """
    Unified AI Gateway providing Prompt Hash Caching, Token & Cost Monitoring,
    and Model Fallback Strategy for High Availability.
    """

    MODEL_RATES = {
        "vllm-primary": {"prompt": 0.0015, "completion": 0.002},
        "vllm-backup": {"prompt": 0.0005, "completion": 0.001},
        "gpt-4o": {"prompt": 0.005, "completion": 0.015},
        "default": {"prompt": 0.001, "completion": 0.002},
    }

    def __init__(
        self,
        redis_client: Optional[aioredis.Redis] = None,
        primary_model_name: str = "vllm-primary",
        fallback_model_name: str = "vllm-backup",
        default_timeout: float = 5.0,
        cache_ttl: int = 3600,
    ):
        self.redis_client = redis_client
        self.primary_model_name = primary_model_name
        self.fallback_model_name = fallback_model_name
        self.default_timeout = default_timeout
        self.cache_ttl = cache_ttl

    async def _get_redis(self) -> Optional[aioredis.Redis]:
        """Lazy getter for Redis client."""
        if self.redis_client is not None:
            return self.redis_client
        try:
            return await get_redis_client()
        except Exception as e:
            logger.warning(f"Failed to obtain Redis client: {e}")
            return None

    def _hash_prompt(self, prompt: str, model_name: str) -> str:
        """Computes SHA-256 hash for prompt and model combination."""
        raw_key = f"{model_name}:{prompt.strip()}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def estimate_tokens(self, text: str) -> int:
        """Estimates token count for given text."""
        if not text:
            return 0
        clean_text = text.strip()
        # Basic heuristic: ~3.5 chars per token for English/mix, 1 token per CJK char
        cjk_chars = sum(1 for c in clean_text if '\u4e00' <= c <= '\u9fff')
        non_cjk_len = len(clean_text) - cjk_chars
        tokens = cjk_chars + max(1, non_cjk_len // 4)
        return max(1, tokens)

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int, model_name: str) -> float:
        """Calculates estimated USD cost for model request."""
        rates = self.MODEL_RATES.get(model_name, self.MODEL_RATES["default"])
        prompt_cost = (prompt_tokens / 1000.0) * rates["prompt"]
        completion_cost = (completion_tokens / 1000.0) * rates["completion"]
        return round(prompt_cost + completion_cost, 6)

    async def get_cached_response(self, prompt: str, model_name: str) -> Optional[Dict[str, Any]]:
        """Retrieves cached response from Redis if exists."""
        redis = await self._get_redis()
        if not redis:
            return None
        cache_key = f"prompt_cache:{self._hash_prompt(prompt, model_name)}"
        try:
            cached_str = await redis.get(cache_key)
            if cached_str:
                if isinstance(cached_str, bytes):
                    cached_str = cached_str.decode("utf-8")
                return json.loads(cached_str)
        except Exception as e:
            logger.warning(f"Redis Prompt Cache read error: {e}")
        return None

    async def set_cached_response(
        self, prompt: str, model_name: str, response_data: Dict[str, Any], ttl: Optional[int] = None
    ) -> bool:
        """Stores response in Redis cache with TTL."""
        redis = await self._get_redis()
        if not redis:
            return False
        cache_key = f"prompt_cache:{self._hash_prompt(prompt, model_name)}"
        effective_ttl = ttl if ttl is not None else self.cache_ttl
        try:
            serialized = json.dumps(response_data, ensure_ascii=False)
            await redis.set(cache_key, serialized, ex=effective_ttl)
            return True
        except Exception as e:
            logger.warning(f"Redis Prompt Cache write error: {e}")
            return False

    async def record_token_stats(
        self, prompt_tokens: int, completion_tokens: int, cost: float, model_name: str
    ) -> None:
        """Records token consumption and cost logs in Redis."""
        redis = await self._get_redis()
        if not redis:
            return
        summary_key = "token_stats:summary"
        try:
            await redis.hincrby(summary_key, "total_prompt_tokens", prompt_tokens)
            await redis.hincrby(summary_key, "total_completion_tokens", completion_tokens)
            await redis.hincrby(summary_key, "total_calls", 1)
            
            # Redis HINCRBYFLOAT for cost
            await redis.hincrbyfloat(summary_key, "total_cost", cost)
            
            # Also append structured log entry
            log_entry = json.dumps({
                "model": model_name,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "cost": cost,
            }, ensure_ascii=False)
            await redis.rpush("token_stats:logs", log_entry)
        except Exception as e:
            logger.warning(f"Failed to record token stats in Redis: {e}")

    async def get_token_stats(self) -> Dict[str, Any]:
        """Aggregates and returns current token usage and cost stats."""
        redis = await self._get_redis()
        default_stats = {
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "total_calls": 0,
        }
        if not redis:
            return default_stats
        try:
            raw_summary = await redis.hgetall("token_stats:summary")
            if not raw_summary:
                return default_stats
            
            # Helper to decode bytes or str keys/vals
            decoded = {}
            for k, v in raw_summary.items():
                key_str = k.decode("utf-8") if isinstance(k, bytes) else str(k)
                val_str = v.decode("utf-8") if isinstance(v, bytes) else str(v)
                decoded[key_str] = val_str

            prompt_toks = int(decoded.get("total_prompt_tokens", 0))
            comp_toks = int(decoded.get("total_completion_tokens", 0))
            cost_val = float(decoded.get("total_cost", 0.0))
            calls_val = int(decoded.get("total_calls", 0))

            return {
                "total_prompt_tokens": prompt_toks,
                "total_completion_tokens": comp_toks,
                "total_tokens": prompt_toks + comp_toks,
                "total_cost": round(cost_val, 6),
                "total_calls": calls_val,
            }
        except Exception as e:
            logger.warning(f"Failed to retrieve token stats from Redis: {e}")
            return default_stats

    async def generate_response(
        self,
        prompt: str,
        primary_func: Optional[Callable[[str], Awaitable[str]]] = None,
        fallback_func: Optional[Callable[[str], Awaitable[str]]] = None,
        timeout: Optional[float] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Executes LLM request with Cache lookup, Token Monitoring, and Model Fallback.
        """
        effective_timeout = timeout if timeout is not None else self.default_timeout

        # 1. Prompt Cache Lookup
        if use_cache:
            cached = await self.get_cached_response(prompt, self.primary_model_name)
            if cached:
                logger.info("Prompt Hash Cache hit!")
                return {
                    "content": cached.get("content", ""),
                    "cached": True,
                    "model_used": cached.get("model_used", self.primary_model_name),
                    "fallback_triggered": False,
                    "prompt_tokens": cached.get("prompt_tokens", 0),
                    "completion_tokens": cached.get("completion_tokens", 0),
                    "cost": 0.0,
                }

        # Default dummy callables for testing/fallback if none supplied
        async def _default_primary(p: str) -> str:
            return f"[Primary Model Response]: {p}"

        async def _default_fallback(p: str) -> str:
            return f"[Fallback Model Response]: {p}"

        actual_primary = primary_func or _default_primary
        actual_fallback = fallback_func or _default_fallback

        # 2. Try Primary Model with Timeout
        try:
            response_text = await asyncio.wait_for(actual_primary(prompt), timeout=effective_timeout)
            prompt_tokens = self.estimate_tokens(prompt)
            completion_tokens = self.estimate_tokens(response_text)
            cost = self.calculate_cost(prompt_tokens, completion_tokens, self.primary_model_name)

            await self.record_token_stats(prompt_tokens, completion_tokens, cost, self.primary_model_name)

            result = {
                "content": response_text,
                "cached": False,
                "model_used": self.primary_model_name,
                "fallback_triggered": False,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "cost": cost,
            }

            if use_cache:
                await self.set_cached_response(prompt, self.primary_model_name, result)

            return result

        except Exception as err:
            logger.warning(
                f"Primary model ({self.primary_model_name}) failed or timed out: {err}. Triggering Fallback strategy."
            )
            
            # 3. Fallback Model Execution
            try:
                response_text = await actual_fallback(prompt)
            except Exception as fb_err:
                logger.error(f"Fallback model ({self.fallback_model_name}) also failed: {fb_err}")
                response_text = f"[System Error]: Both primary and fallback models failed. Details: {fb_err}"

            prompt_tokens = self.estimate_tokens(prompt)
            completion_tokens = self.estimate_tokens(response_text)
            cost = self.calculate_cost(prompt_tokens, completion_tokens, self.fallback_model_name)

            await self.record_token_stats(prompt_tokens, completion_tokens, cost, self.fallback_model_name)

            fallback_result = {
                "content": response_text,
                "cached": False,
                "model_used": self.fallback_model_name,
                "fallback_triggered": True,
                "primary_error": str(err),
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "cost": cost,
            }

            if use_cache:
                await self.set_cached_response(prompt, self.fallback_model_name, fallback_result)

            return fallback_result
