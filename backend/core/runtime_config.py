"""Runtime Configuration Manager for Admin-Controlled LLM & LangGraph Node Policies.

Provides thread-safe reading, validated hot-updating, baseline reset,
and JSON persistence for whitelisted runtime parameters while strictly
preventing exposure or tampering of sensitive secrets (LLM_API_KEY, SECRET_KEY).
"""

from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import threading
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator

from backend.core.config import settings

logger = logging.getLogger(__name__)

LLMProviderType = Literal["auto", "openai", "deepseek", "vllm", "ollama", "local_fallback"]

WHITELIST_KEYS = (
    "llm_provider",
    "llm_model",
    "llm_api_base",
    "llm_thinking",
    "llm_temperature",
    "llm_max_tokens",
    "rag_top_k",
    "rag_min_score",
    "system_prompt_instruction",
    "router_llm_enabled",
    "router_llm_timeout",
    "query_rewriter_llm_enabled",
    "query_rewriter_llm_timeout",
    "slot_extractor_llm_enabled",
    "slot_extractor_llm_timeout",
)

# Persisted under gitignored <repo_root>/logs/ directory regardless of working directory
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RUNTIME_CONFIG_PATH = _PROJECT_ROOT / "logs" / "runtime_config.json"

_LOCK = threading.RLock()
_ALLOWED_PROVIDERS = ("auto", "openai", "deepseek", "vllm", "ollama", "local_fallback")

# Capture immutable startup baseline from settings
_BASELINE: Dict[str, Any] = {
    "llm_provider": settings.LLM_PROVIDER if settings.LLM_PROVIDER in _ALLOWED_PROVIDERS else "auto",
    "llm_model": (settings.LLM_MODEL or "deepseek-chat").strip() or "deepseek-chat",
    "llm_api_base": settings.LLM_API_BASE.strip().rstrip("/") if settings.LLM_API_BASE and settings.LLM_API_BASE.strip() else None,
    "llm_thinking": bool(settings.LLM_THINKING),
    "llm_temperature": float(settings.LLM_TEMPERATURE),
    "llm_max_tokens": int(settings.LLM_MAX_TOKENS),
    "rag_top_k": 3,
    "rag_min_score": 0.16,
    "system_prompt_instruction": "",
    "router_llm_enabled": bool(getattr(settings, "ROUTER_LLM_ENABLED", True)),
    "router_llm_timeout": float(getattr(settings, "ROUTER_LLM_TIMEOUT", 2.5)),
    "query_rewriter_llm_enabled": bool(getattr(settings, "QUERY_REWRITER_LLM_ENABLED", True)),
    "query_rewriter_llm_timeout": float(getattr(settings, "QUERY_REWRITER_LLM_TIMEOUT", 2.5)),
    "slot_extractor_llm_enabled": bool(getattr(settings, "SLOT_EXTRACTOR_LLM_ENABLED", True)),
    "slot_extractor_llm_timeout": float(getattr(settings, "SLOT_EXTRACTOR_LLM_TIMEOUT", 2.5)),
}
_BASELINE_API_KEY: Optional[str] = settings.LLM_API_KEY


class RuntimeConfigValues(BaseModel):
    """Validated runtime parameter snapshot."""

    llm_provider: LLMProviderType = "auto"
    llm_model: str = Field(default="deepseek-chat", min_length=1, max_length=120)
    llm_api_base: Optional[str] = Field(default=None, max_length=300)
    llm_thinking: bool = False
    llm_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(default=4096, ge=128, le=16384)
    rag_top_k: int = Field(default=3, ge=1, le=20)
    rag_min_score: float = Field(default=0.16, ge=0.0, le=1.0)
    system_prompt_instruction: str = Field(default="", max_length=2000)
    router_llm_enabled: bool = True
    router_llm_timeout: float = Field(default=2.5, ge=0.2, le=15.0, allow_inf_nan=False)
    query_rewriter_llm_enabled: bool = True
    query_rewriter_llm_timeout: float = Field(default=2.5, ge=0.2, le=15.0, allow_inf_nan=False)
    slot_extractor_llm_enabled: bool = True
    slot_extractor_llm_timeout: float = Field(default=2.5, ge=0.2, le=15.0, allow_inf_nan=False)

    @field_validator("llm_api_base")
    @classmethod
    def validate_api_base(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        if not (cleaned.startswith("http://") or cleaned.startswith("https://")):
            raise ValueError("LLM_API_BASE 必须以 http:// 或 https:// 开头")
        return cleaned.rstrip("/")

    @field_validator("llm_model")
    @classmethod
    def validate_model_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("模型名称不能为空")
        return cleaned

    @field_validator("system_prompt_instruction")
    @classmethod
    def normalize_instruction(cls, value: str) -> str:
        return value.strip() if value else ""


class _RuntimeMeta:
    updated_at: Optional[str] = None
    updated_by: Optional[str] = None
    rag_top_k: int = _BASELINE["rag_top_k"]
    rag_min_score: float = _BASELINE["rag_min_score"]
    system_prompt_instruction: str = _BASELINE["system_prompt_instruction"]


_META = _RuntimeMeta()


def mask_secret(secret: Optional[str]) -> str:
    """Returns a non-reversible masked representation of an API key."""
    if not secret or not secret.strip():
        return "未配置"
    cleaned = secret.strip()
    if len(cleaned) <= 8:
        return "**** (已配置)"
    return f"{cleaned[:3]}****{cleaned[-4:]}"


def _sync_to_settings(cfg: RuntimeConfigValues) -> None:
    """Propagates whitelisted configuration values onto the live Settings singleton."""
    settings.LLM_PROVIDER = cfg.llm_provider
    settings.LLM_MODEL = cfg.llm_model
    settings.LLM_API_BASE = cfg.llm_api_base
    settings.LLM_THINKING = cfg.llm_thinking
    settings.LLM_TEMPERATURE = cfg.llm_temperature
    settings.LLM_MAX_TOKENS = cfg.llm_max_tokens
    settings.ROUTER_LLM_ENABLED = cfg.router_llm_enabled
    settings.ROUTER_LLM_TIMEOUT = cfg.router_llm_timeout
    settings.QUERY_REWRITER_LLM_ENABLED = cfg.query_rewriter_llm_enabled
    settings.QUERY_REWRITER_LLM_TIMEOUT = cfg.query_rewriter_llm_timeout
    settings.SLOT_EXTRACTOR_LLM_ENABLED = cfg.slot_extractor_llm_enabled
    settings.SLOT_EXTRACTOR_LLM_TIMEOUT = cfg.slot_extractor_llm_timeout

    _META.rag_top_k = cfg.rag_top_k
    _META.rag_min_score = cfg.rag_min_score
    _META.system_prompt_instruction = cfg.system_prompt_instruction


def _load_persisted_overrides() -> None:
    """Loads persisted non-secret overrides from disk at module import if present."""
    with _LOCK:
        if not RUNTIME_CONFIG_PATH.exists():
            return
        try:
            raw_text = RUNTIME_CONFIG_PATH.read_text(encoding="utf-8")
            payload = json.loads(raw_text)
            if not isinstance(payload, dict):
                return
            filtered = {k: payload[k] for k in WHITELIST_KEYS if k in payload}
            if not filtered:
                return
            merged = {**_BASELINE, **filtered}
            validated = RuntimeConfigValues(**merged)
            _sync_to_settings(validated)
            _META.updated_at = payload.get("updated_at")
            _META.updated_by = payload.get("updated_by")
            logger.info("[RuntimeConfig] Loaded persisted overrides from %s", RUNTIME_CONFIG_PATH)
        except Exception as exc:
            logger.warning("[RuntimeConfig] Failed to load %s (%s). Using baseline defaults.", RUNTIME_CONFIG_PATH, exc)


def _persist_overrides(cfg: RuntimeConfigValues) -> None:
    """Persists non-secret whitelisted overrides to disk cleanly."""
    payload = {
        **cfg.model_dump(),
        "updated_at": _META.updated_at,
        "updated_by": _META.updated_by,
    }
    try:
        RUNTIME_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        RUNTIME_CONFIG_PATH.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        logger.warning("[RuntimeConfig] Disk persistence skipped due to I/O error: %s", exc)


def get_runtime_config() -> RuntimeConfigValues:
    """Returns current effective runtime configuration synchronized with Settings."""
    with _LOCK:
        provider = settings.LLM_PROVIDER
        allowed_providers = ("auto", "openai", "deepseek", "vllm", "ollama", "local_fallback")
        if provider not in allowed_providers:
            provider = "auto"
        return RuntimeConfigValues(
            llm_provider=provider,  # type: ignore[arg-type]
            llm_model=(settings.LLM_MODEL or "").strip() or _BASELINE["llm_model"],
            llm_api_base=settings.LLM_API_BASE,
            llm_thinking=bool(settings.LLM_THINKING),
            llm_temperature=float(settings.LLM_TEMPERATURE),
            llm_max_tokens=int(settings.LLM_MAX_TOKENS),
            rag_top_k=int(_META.rag_top_k),
            rag_min_score=float(_META.rag_min_score),
            system_prompt_instruction=_META.system_prompt_instruction,
            router_llm_enabled=bool(getattr(settings, "ROUTER_LLM_ENABLED", True)),
            router_llm_timeout=float(getattr(settings, "ROUTER_LLM_TIMEOUT", 2.5)),
            query_rewriter_llm_enabled=bool(getattr(settings, "QUERY_REWRITER_LLM_ENABLED", True)),
            query_rewriter_llm_timeout=float(getattr(settings, "QUERY_REWRITER_LLM_TIMEOUT", 2.5)),
            slot_extractor_llm_enabled=bool(getattr(settings, "SLOT_EXTRACTOR_LLM_ENABLED", True)),
            slot_extractor_llm_timeout=float(getattr(settings, "SLOT_EXTRACTOR_LLM_TIMEOUT", 2.5)),
        )


def update_runtime_config(
    updates: Dict[str, Any],
    updated_by: str = "admin",
    llm_api_key: Optional[str] = None,
    clear_api_key: bool = False,
) -> RuntimeConfigValues:
    """Validates and hot-applies whitelisted runtime configuration updates."""
    with _LOCK:
        current = get_runtime_config().model_dump()
        for key, value in updates.items():
            if key in WHITELIST_KEYS and value is not None:
                current[key] = value
            elif key == "llm_api_base" and value is None:
                # Allow explicitly clearing api_base back to None
                current["llm_api_base"] = None

        validated = RuntimeConfigValues(**current)
        _sync_to_settings(validated)

        if clear_api_key:
            settings.LLM_API_KEY = None
        elif llm_api_key is not None:
            cleaned_key = llm_api_key.strip()
            if cleaned_key and "****" not in cleaned_key:
                settings.LLM_API_KEY = cleaned_key

        _META.updated_at = datetime.now(timezone.utc).isoformat()
        _META.updated_by = updated_by
        _persist_overrides(validated)
        return validated


def reset_runtime_config(updated_by: str = "admin") -> RuntimeConfigValues:
    """Restores all runtime parameters and API key back to startup baseline defaults."""
    with _LOCK:
        baseline_cfg = RuntimeConfigValues(**_BASELINE)
        _sync_to_settings(baseline_cfg)
        settings.LLM_API_KEY = _BASELINE_API_KEY
        _META.updated_at = datetime.now(timezone.utc).isoformat()
        _META.updated_by = updated_by
        try:
            if RUNTIME_CONFIG_PATH.exists():
                RUNTIME_CONFIG_PATH.unlink()
        except OSError as exc:
            logger.warning("[RuntimeConfig] Failed to unlink persisted config on reset: %s", exc)
        return baseline_cfg


def get_available_providers() -> List[Dict[str, Any]]:
    """Returns curated provider & model presets for Admin Settings Workbench."""
    return [
        {
            "id": "auto",
            "label": "自动路由 / 智能降级",
            "description": "存在外部密钥或底座地址时优先调用远程模型，否则自动切换离线本地合成引擎",
            "default_model": "deepseek-chat",
            "default_api_base": "",
            "supports_thinking": False,
        },
        {
            "id": "ollama",
            "label": "Ollama 本地推理引擎",
            "description": "原生 /api/chat 驱动，支持极速模式 (think=false) 与深度思考 CoT 切换",
            "default_model": "qwen3.5:2b",
            "default_api_base": "http://127.0.0.1:11434",
            "supports_thinking": True,
        },
        {
            "id": "deepseek",
            "label": "DeepSeek 深度求索",
            "description": "兼容 DeepSeek Chat / DeepSeek Reasoner 官方云端接口",
            "default_model": "deepseek-chat",
            "default_api_base": "https://api.deepseek.com/v1",
            "supports_thinking": True,
        },
        {
            "id": "openai",
            "label": "OpenAI 兼容接口",
            "description": "适配通义千问 DashScope、硅基流动及标准 OpenAI /v1 协议端点",
            "default_model": "gpt-4o-mini",
            "default_api_base": "https://api.openai.com/v1",
            "supports_thinking": False,
        },
        {
            "id": "vllm",
            "label": "vLLM 私有化推理集群",
            "description": "高吞吐企业内网 vLLM OpenAI-Compatible 部署服务",
            "default_model": "Qwen/Qwen2.5-7B-Instruct",
            "default_api_base": "http://127.0.0.1:8000/v1",
            "supports_thinking": False,
        },
        {
            "id": "local_fallback",
            "label": "零依赖离线安全合成",
            "description": "不请求任何外部模型 API，基于本地制度切片与工具执行结果确定性生成",
            "default_model": "local-enterprise-agent-v1",
            "default_api_base": "",
            "supports_thinking": False,
        },
    ]


def resolve_active_engine_name(cfg: Optional[RuntimeConfigValues] = None) -> str:
    """Resolves the concrete LLM adapter class name selected for current runtime config."""
    resolved = cfg or get_runtime_config()
    has_api_key = bool(settings.LLM_API_KEY and settings.LLM_API_KEY.strip())
    if resolved.llm_provider == "local_fallback":
        return "LocalEnterpriseChatModel"
    if resolved.llm_provider == "ollama":
        return "NativeOllamaChatModel"
    if has_api_key or resolved.llm_api_base or resolved.llm_provider in ("openai", "deepseek", "vllm"):
        return "ChatOpenAI"
    return "LocalEnterpriseChatModel"


def get_sanitized_admin_config() -> Dict[str, Any]:
    """Builds sanitized configuration payload for Admin API responses.

    NEVER includes plaintext LLM_API_KEY or SECRET_KEY.
    """
    with _LOCK:
        cfg = get_runtime_config()
        has_api_key = bool(settings.LLM_API_KEY and settings.LLM_API_KEY.strip())
        has_jwt_secret = bool(settings.SECRET_KEY and settings.SECRET_KEY.strip())
        active_engine = resolve_active_engine_name(cfg)

        return {
            **cfg.model_dump(),
            "api_key_configured": has_api_key,
            "api_key_masked": mask_secret(settings.LLM_API_KEY),
            "jwt_secret_configured": has_jwt_secret,
            "jwt_secret_masked": "****** (HS256 已启用保护)" if has_jwt_secret else "未配置",
            "active_engine": active_engine,
            "updated_at": _META.updated_at,
            "updated_by": _META.updated_by,
            "defaults": dict(_BASELINE),
            "providers": get_available_providers(),
        }


# Load persisted non-secret overrides if present on disk
_load_persisted_overrides()
