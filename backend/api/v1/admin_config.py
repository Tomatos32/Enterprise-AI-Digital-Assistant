"""Admin-Exclusive Runtime LLM & LangGraph Node Configuration Router."""

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional
import httpx
from fastapi import APIRouter, Body, Depends
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from backend.core.config import settings
from backend.core.exceptions import AppException, StandardResponse
from backend.core.llm import get_llm_info
from backend.core.rbac import RoleEnum, UserPayload, require_role
from backend.core.runtime_config import (
    LLMProviderType,
    get_runtime_config,
    get_sanitized_admin_config,
    reset_runtime_config,
    update_runtime_config,
)
from backend.rag.vector_store import get_qdrant_info

logger = logging.getLogger(__name__)

router = APIRouter()


class AdminConfigUpdateRequest(BaseModel):
    """Validated payload for hot-updating whitelisted LLM & RAG node settings."""

    model_config = ConfigDict(extra="ignore")

    llm_provider: Optional[LLMProviderType] = Field(
        default=None,
        description="大模型驱动引擎 (auto / ollama / deepseek / openai / vllm / local_fallback)",
    )
    llm_model: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=120,
        description="模型标识符",
    )
    llm_api_base: Optional[str] = Field(
        default=None,
        max_length=300,
        description="模型服务基础 URL (http:// 或 https://)",
    )
    llm_thinking: Optional[bool] = Field(
        default=None,
        description="是否开启深度思考 CoT 模式 (true=深度推理, false=极速模式)",
    )
    llm_temperature: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="生成采样温度 [0.0, 2.0]",
    )
    llm_max_tokens: Optional[int] = Field(
        default=None,
        ge=128,
        le=16384,
        description="最大生成 Token 预算 [128, 16384]",
    )
    rag_top_k: Optional[int] = Field(
        default=None,
        ge=1,
        le=20,
        description="RAG 混合检索召回片段数 Top-K [1, 20]",
    )
    rag_min_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Rerank 语义相关性截断阈值 [0.0, 1.0]",
    )
    system_prompt_instruction: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="附加给企业数字员工的系统级行为规范指令",
    )
    # Write-only secret update channel; NEVER returned in plaintext
    llm_api_key: Optional[str] = Field(
        default=None,
        max_length=300,
        description="可选：仅写入的新 API Key（空字符串或含掩码将保留原密钥）",
    )
    clear_api_key: bool = Field(
        default=False,
        description="设为 true 时显式清空内存中已配置的外部 API Key",
    )

    @field_validator("llm_api_base")
    @classmethod
    def validate_api_base(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return ""
        if not (cleaned.startswith("http://") or cleaned.startswith("https://")):
            raise ValueError("LLM_API_BASE 必须以 http:// 或 https:// 开头")
        return cleaned.rstrip("/")


class AdminConfigProbeRequest(BaseModel):
    """Optional preview parameters for testing model endpoint connectivity."""

    model_config = ConfigDict(extra="ignore")

    llm_provider: Optional[LLMProviderType] = None
    llm_model: Optional[str] = Field(default=None, max_length=120)
    llm_api_base: Optional[str] = Field(default=None, max_length=300)
    llm_thinking: Optional[bool] = None

    @field_validator("llm_api_base")
    @classmethod
    def validate_probe_base(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return ""
        if not (cleaned.startswith("http://") or cleaned.startswith("https://")):
            raise ValueError("探测地址必须以 http:// 或 https:// 开头")
        return cleaned.rstrip("/")


def _resolve_probe_base(provider: str, raw_base: Optional[str]) -> str:
    """Resolves normalized endpoint base URL for connectivity probing."""
    base = (raw_base or "").strip()
    if not base:
        if provider == "deepseek":
            base = "https://api.deepseek.com/v1"
        elif provider == "ollama":
            base = "http://127.0.0.1:11434"
        elif provider == "vllm":
            base = "http://127.0.0.1:8000/v1"
        elif provider in ("openai", "auto"):
            base = "https://api.openai.com/v1"
    if "localhost" in base:
        base = base.replace("localhost", "127.0.0.1")
    return base.rstrip("/")


@router.get("", response_model=StandardResponse)
async def get_admin_runtime_config(
    current_user: UserPayload = Depends(require_role([RoleEnum.ADMIN])),
):
    """Returns sanitized LLM, RAG, and LangGraph runtime settings for Admins only."""
    payload = get_sanitized_admin_config()
    payload["llm_telemetry"] = get_llm_info()
    return StandardResponse(
        code=200,
        message="管理员运行时配置读取成功",
        data=payload,
    )


@router.put("", response_model=StandardResponse)
async def update_admin_runtime_config(
    body: AdminConfigUpdateRequest,
    current_user: UserPayload = Depends(require_role([RoleEnum.ADMIN])),
):
    """Validates and hot-applies whitelisted LLM & LangGraph node settings for Admins only."""
    raw_updates: Dict[str, Any] = body.model_dump(
        exclude={"llm_api_key", "clear_api_key"},
        exclude_unset=True,
    )
    if "llm_api_base" in raw_updates and raw_updates["llm_api_base"] == "":
        raw_updates["llm_api_base"] = None

    try:
        update_runtime_config(
            updates=raw_updates,
            updated_by=current_user.username,
            llm_api_key=body.llm_api_key,
            clear_api_key=body.clear_api_key,
        )
    except (ValidationError, ValueError) as exc:
        raise AppException(message=f"参数校验失败: {exc}", code=400) from exc

    payload = get_sanitized_admin_config()
    payload["llm_telemetry"] = get_llm_info()
    return StandardResponse(
        code=200,
        message="配置已保存并热生效",
        data=payload,
    )


@router.post("/reset", response_model=StandardResponse)
async def reset_admin_runtime_config(
    current_user: UserPayload = Depends(require_role([RoleEnum.ADMIN])),
):
    """Restores all runtime parameters back to startup baseline defaults."""
    reset_runtime_config(updated_by=current_user.username)
    payload = get_sanitized_admin_config()
    payload["llm_telemetry"] = get_llm_info()
    return StandardResponse(
        code=200,
        message="已恢复为系统启动默认配置",
        data=payload,
    )


def _build_probe_data(
    *,
    reachable: bool,
    status: str,
    provider: str,
    model: str,
    endpoint: str,
    thinking: bool,
    latency_ms: float,
    detail: str,
    qdrant_info: Dict[str, Any],
    available_models: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Constructs uniform diagnostic payload for connectivity probe responses."""
    return {
        "reachable": reachable,
        "status": status,
        "provider": provider,
        "model": model,
        "endpoint": endpoint,
        "thinking": thinking,
        "latency_ms": latency_ms,
        "available_models": available_models or [],
        "rag_status": qdrant_info.get("status", "healthy"),
        "rag_points": qdrant_info.get("points_count", 0),
        "detail": detail,
    }


@router.post("/probe", response_model=StandardResponse)
async def probe_admin_runtime_connectivity(
    body: Optional[AdminConfigProbeRequest] = Body(default=None),
    current_user: UserPayload = Depends(require_role([RoleEnum.ADMIN])),
):
    """Executes non-destructive connectivity & readiness probe for LLM endpoint and RAG store."""
    cfg = get_runtime_config()
    target_provider = (body.llm_provider if body and body.llm_provider else cfg.llm_provider)
    target_model = (body.llm_model if body and body.llm_model else cfg.llm_model)
    if body and body.llm_api_base is not None:
        target_base = body.llm_api_base or None
    else:
        target_base = cfg.llm_api_base
    target_thinking = (
        body.llm_thinking
        if body and body.llm_thinking is not None
        else cfg.llm_thinking
    )

    has_key = bool(settings.LLM_API_KEY and settings.LLM_API_KEY.strip())
    qdrant_info = await asyncio.to_thread(get_qdrant_info)
    started = time.perf_counter()

    # 1. Offline deterministic synthesis engine
    if target_provider == "local_fallback" or (
        target_provider == "auto" and not has_key and not target_base
    ):
        latency_ms = round((time.perf_counter() - started) * 1000, 1)
        return StandardResponse(
            code=200,
            message="离线确定性合成引擎与检索管道就绪",
            data=_build_probe_data(
                reachable=True,
                status="READY",
                provider=target_provider,
                model="local-enterprise-agent-v1",
                endpoint="built-in-local",
                thinking=target_thinking,
                latency_ms=latency_ms,
                available_models=["local-enterprise-agent-v1"],
                qdrant_info=qdrant_info,
                detail="当前运行于零依赖本地兜底合成引擎，无需外部算力连接即可响应问答。",
            ),
        )

    resolved_base = _resolve_probe_base(target_provider, target_base)
    is_local = any(host in resolved_base for host in ("127.0.0.1", "localhost", "0.0.0.0"))

    # 2. Native Ollama endpoint probe
    if target_provider == "ollama":
        native_base = resolved_base.replace("/v1", "").rstrip("/")
        probe_url = f"{native_base}/api/tags"
        try:
            async with httpx.AsyncClient(trust_env=False, timeout=3.0) as client:
                resp = await client.get(probe_url)
            latency_ms = round((time.perf_counter() - started) * 1000, 1)
            if resp.status_code == 200:
                tags_payload = resp.json()
                models: List[str] = [
                    str(m.get("name"))
                    for m in tags_payload.get("models", [])
                    if isinstance(m, dict) and m.get("name")
                ]
                model_found = target_model in models or any(
                    m.startswith(f"{target_model}:") for m in models
                )
                return StandardResponse(
                    code=200,
                    message="Ollama 服务连通性正常" if model_found else "Ollama 服务在线，但目标模型尚未拉取",
                    data=_build_probe_data(
                        reachable=True,
                        status="HEALTHY" if model_found else "MODEL_MISSING",
                        provider=target_provider,
                        model=target_model,
                        endpoint=native_base,
                        thinking=target_thinking,
                        latency_ms=latency_ms,
                        available_models=models[:12],
                        qdrant_info=qdrant_info,
                        detail=(
                            f"已检测到模型 {target_model}，可支持{'深度思考 CoT' if target_thinking else '极速响应'}模式。"
                            if model_found
                            else f"Ollama 已在线（{len(models)} 个可用模型），但未找到 {target_model}。"
                        ),
                    ),
                )
            return StandardResponse(
                code=200,
                message=f"Ollama 返回异常状态码 HTTP {resp.status_code}",
                data=_build_probe_data(
                    reachable=False,
                    status="HTTP_ERROR",
                    provider=target_provider,
                    model=target_model,
                    endpoint=native_base,
                    thinking=target_thinking,
                    latency_ms=latency_ms,
                    qdrant_info=qdrant_info,
                    detail=f"探针收到 HTTP {resp.status_code}，对话链路将自动启用本地合成兜底。",
                ),
            )
        except Exception as exc:
            latency_ms = round((time.perf_counter() - started) * 1000, 1)
            logger.info("[AdminProbe] Ollama probe fallback (%s): %s", native_base, type(exc).__name__)
            return StandardResponse(
                code=200,
                message="本地 Ollama 服务未启动或不可达，已就绪离线兜底",
                data=_build_probe_data(
                    reachable=False,
                    status="FALLBACK_READY",
                    provider=target_provider,
                    model=target_model,
                    endpoint=native_base,
                    thinking=target_thinking,
                    latency_ms=latency_ms,
                    qdrant_info=qdrant_info,
                    detail=f"无法连接 {native_base} ({type(exc).__name__})，问答请求将通过 ResilientChatModel 自动切换离线兜底。",
                ),
            )

    # 3. OpenAI-compatible remote/cluster probe (DeepSeek / OpenAI / vLLM / Auto)
    probe_url = f"{resolved_base}/models"
    headers: Dict[str, str] = {}
    if has_key and settings.LLM_API_KEY:
        headers["Authorization"] = f"Bearer {settings.LLM_API_KEY}"

    try:
        async with httpx.AsyncClient(trust_env=not is_local, timeout=3.5) as client:
            resp = await client.get(probe_url, headers=headers)
        latency_ms = round((time.perf_counter() - started) * 1000, 1)

        if resp.status_code == 200:
            payload = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            model_ids = [
                str(item.get("id"))
                for item in payload.get("data", [])
                if isinstance(item, dict) and item.get("id")
            ]
            return StandardResponse(
                code=200,
                message="OpenAI 兼容模型网关连通正常",
                data=_build_probe_data(
                    reachable=True,
                    status="HEALTHY",
                    provider=target_provider,
                    model=target_model,
                    endpoint=resolved_base,
                    thinking=target_thinking,
                    latency_ms=latency_ms,
                    available_models=model_ids[:12],
                    qdrant_info=qdrant_info,
                    detail=f"网关响应正常（延迟 {latency_ms} ms），当前配置模型：{target_model}。",
                ),
            )

        if resp.status_code in (401, 403):
            return StandardResponse(
                code=200,
                message="模型网关鉴权未通过，请核对 API Key",
                data=_build_probe_data(
                    reachable=False,
                    status="AUTH_ERROR",
                    provider=target_provider,
                    model=target_model,
                    endpoint=resolved_base,
                    thinking=target_thinking,
                    latency_ms=latency_ms,
                    qdrant_info=qdrant_info,
                    detail=f"端点返回 HTTP {resp.status_code}，请确认密钥有效性（密钥未在返回中回显）。",
                ),
            )

        return StandardResponse(
            code=200,
            message=f"模型端点返回状态码 HTTP {resp.status_code}",
            data=_build_probe_data(
                reachable=False,
                status="HTTP_ERROR",
                provider=target_provider,
                model=target_model,
                endpoint=resolved_base,
                thinking=target_thinking,
                latency_ms=latency_ms,
                qdrant_info=qdrant_info,
                detail=f"探针端点返回 HTTP {resp.status_code}，系统已开启故障自愈兜底。",
            ),
        )
    except Exception as exc:
        latency_ms = round((time.perf_counter() - started) * 1000, 1)
        logger.info("[AdminProbe] Remote probe fallback (%s): %s", resolved_base, type(exc).__name__)
        return StandardResponse(
            code=200,
            message="远程模型网关暂不可达，已就绪离线兜底",
            data=_build_probe_data(
                reachable=False,
                status="FALLBACK_READY",
                provider=target_provider,
                model=target_model,
                endpoint=resolved_base,
                thinking=target_thinking,
                latency_ms=latency_ms,
                qdrant_info=qdrant_info,
                detail=f"无法连接 {resolved_base} ({type(exc).__name__})，问答请求将自动回退离线合成引擎。",
            ),
        )
