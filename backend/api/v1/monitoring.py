"""Admin-Exclusive System Telemetry, Tool Audit & Enterprise SLA Monitoring Router."""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, Query
from prometheus_client import REGISTRY
from sqlalchemy import func
from sqlalchemy.orm import Session

import backend.tools.impl  # noqa: F401  # Ensure all built-in tools are registered in ToolRegistry
from backend.api.v1.mock.oa_mock import SLA_METRICS
from backend.core.exceptions import StandardResponse
from backend.core.knowledge_ledger import list_task_records
from backend.core.llm import get_llm_info
from backend.core.metrics import get_cognitive_telemetry_snapshot, get_recent_tool_audits
from backend.core.rbac import RoleEnum, UserPayload, require_role
from backend.core.redis import check_redis_health
from backend.core.runtime_config import get_sanitized_admin_config
from backend.db.session import check_mysql_health, get_db
from backend.models.approval import Approval
from backend.models.chat import ChatMessage, ChatSession
from backend.models.ticket import Ticket
from backend.rag.vector_store import check_qdrant_health, get_qdrant_info
from backend.tools.registry import registry

logger = logging.getLogger(__name__)

router = APIRouter()

# Ordered 5-bucket TTFT boundaries matching llm_time_to_first_token_seconds histogram buckets
TTFT_BUCKET_SPECS: List[Tuple[str, str, Optional[float]]] = [
    ("<= 100ms", "0.1", 100.0),
    ("100ms - 250ms", "0.25", 250.0),
    ("250ms - 500ms", "0.5", 500.0),
    ("500ms - 1.5s", "1.5", 1500.0),
    ("> 1.5s", "+Inf", None),
]

PRIORITY_ORDER: List[str] = ["P0", "P1", "P2", "P3", "P4"]
PRIORITY_META: Dict[str, Dict[str, Any]] = {
    "P0": {"label": "灾难级", "limit_minutes": 30},
    "P1": {"label": "紧急", "limit_minutes": 120},
    "P2": {"label": "重要", "limit_minutes": 480},
    "P3": {"label": "一般", "limit_minutes": 1440},
    "P4": {"label": "咨询", "limit_minutes": 2880},
}
ACTIVE_TASK_STATUSES = {"PENDING", "PROGRESS", "STARTED", "RETRY"}
CLOSED_TICKET_STATUSES = {"RESOLVED", "CLOSED", "DONE", "COMPLETED"}


def _collect_prometheus_snapshot(audit_limit: int) -> Dict[str, Any]:
    """Collects non-cumulative TTFT buckets, token usage, cache rates, WS, Celery, and tool metrics."""
    active_ws = 0
    celery_depth = 0
    cache_hits = 0
    cache_misses = 0

    input_tokens = 0
    output_tokens = 0
    tokens_by_model: Dict[str, Dict[str, int]] = {}

    ttft_raw_buckets: Dict[str, float] = {}
    ttft_total_count = 0
    ttft_total_sum = 0.0

    tool_counts: Dict[str, Dict[str, int]] = {}
    tool_duration_sum: Dict[str, float] = {}
    tool_duration_count: Dict[str, int] = {}

    for metric_family in REGISTRY.collect():
        for sample in metric_family.samples:
            sname = sample.name
            labels = sample.labels or {}
            val = float(sample.value)

            if sname == "active_websocket_connections":
                active_ws = max(0, int(round(val)))
            elif sname == "celery_queue_depth":
                celery_depth = max(0, int(round(val)))
            elif sname == "prompt_cache_hits_total":
                cache_hits += max(0, int(round(val)))
            elif sname == "prompt_cache_misses_total":
                cache_misses += max(0, int(round(val)))
            elif sname == "llm_token_total":
                model_name = str(labels.get("model") or "unknown")
                tok_type = str(labels.get("type") or "input")
                tok_int = max(0, int(round(val)))
                entry = tokens_by_model.setdefault(model_name, {"input": 0, "output": 0})
                if tok_type == "output":
                    output_tokens += tok_int
                    entry["output"] += tok_int
                else:
                    input_tokens += tok_int
                    entry["input"] += tok_int
            elif sname == "llm_time_to_first_token_seconds_bucket":
                le_val = str(labels.get("le") or "")
                if le_val:
                    ttft_raw_buckets[le_val] = val
            elif sname == "llm_time_to_first_token_seconds_count":
                ttft_total_count = max(0, int(round(val)))
            elif sname == "llm_time_to_first_token_seconds_sum":
                ttft_total_sum = max(0.0, val)
            elif sname == "tool_executions_total":
                tname = str(labels.get("tool_name") or "unknown")
                tstatus = str(labels.get("status") or "success")
                tentry = tool_counts.setdefault(tname, {"success": 0, "error": 0})
                if tstatus == "error":
                    tentry["error"] += max(0, int(round(val)))
                else:
                    tentry["success"] += max(0, int(round(val)))
            elif sname == "tool_execution_duration_seconds_sum":
                tname = str(labels.get("tool_name") or "unknown")
                tool_duration_sum[tname] = max(0.0, val)
            elif sname == "tool_execution_duration_seconds_count":
                tname = str(labels.get("tool_name") or "unknown")
                tool_duration_count[tname] = max(0, int(round(val)))

    # Convert cumulative Prometheus histogram buckets into discrete non-cumulative intervals
    ttft_buckets: List[Dict[str, Any]] = []
    prev_cumulative = 0.0
    for label, le_key, upper_ms in TTFT_BUCKET_SPECS:
        if le_key == "+Inf" and "+Inf" not in ttft_raw_buckets:
            cumulative_val = float(ttft_total_count)
        else:
            cumulative_val = float(ttft_raw_buckets.get(le_key, prev_cumulative))
        discrete_count = max(0, int(round(cumulative_val - prev_cumulative)))
        prev_cumulative = max(prev_cumulative, cumulative_val)
        share_pct = round((discrete_count / ttft_total_count) * 100, 1) if ttft_total_count > 0 else 0.0
        ttft_buckets.append(
            {
                "bucket": label,
                "le_key": le_key,
                "upper_ms": upper_ms,
                "count": discrete_count,
                "share_percent": share_pct,
            }
        )

    ttft_avg_ms = round((ttft_total_sum / ttft_total_count) * 1000, 1) if ttft_total_count > 0 else 0.0

    # Prompt cache hit rate
    total_lookups = cache_hits + cache_misses
    cache_hit_rate = round((cache_hits / total_lookups) * 100, 1) if total_lookups > 0 else 0.0

    # Model token breakdown
    model_breakdown: List[Dict[str, Any]] = []
    for model_name, counts in tokens_by_model.items():
        m_total = counts["input"] + counts["output"]
        if m_total > 0:
            model_breakdown.append(
                {
                    "model": model_name,
                    "input_tokens": counts["input"],
                    "output_tokens": counts["output"],
                    "total_tokens": m_total,
                }
            )
    model_breakdown.sort(key=lambda item: item["total_tokens"], reverse=True)

    # Merge ToolRegistry registered tools with Prometheus tool invocation counters
    registered_meta: Dict[str, str] = {}
    for tool_def in registry.get_openai_tools():
        fn = tool_def.get("function", {})
        tname = str(fn.get("name") or "")
        if tname:
            registered_meta[tname] = str(fn.get("description") or "")

    all_tool_names = list(registered_meta.keys())
    for seen_name in sorted(tool_counts.keys()):
        if seen_name not in registered_meta:
            all_tool_names.append(seen_name)

    tool_stats: List[Dict[str, Any]] = []
    total_tool_success = 0
    total_tool_error = 0
    for tname in all_tool_names:
        counts = tool_counts.get(tname, {"success": 0, "error": 0})
        succ = counts["success"]
        err = counts["error"]
        t_total = succ + err
        total_tool_success += succ
        total_tool_error += err
        dur_cnt = tool_duration_count.get(tname, 0)
        avg_ms = round((tool_duration_sum.get(tname, 0.0) / dur_cnt) * 1000, 2) if dur_cnt > 0 else 0.0
        succ_rate = round((succ / t_total) * 100, 1) if t_total > 0 else 0.0
        tool_stats.append(
            {
                "tool_name": tname,
                "description": registered_meta.get(tname, "动态调用工具"),
                "registered": tname in registered_meta,
                "success_count": succ,
                "error_count": err,
                "total_count": t_total,
                "success_rate_percent": succ_rate,
                "avg_latency_ms": avg_ms,
            }
        )
    tool_stats.sort(key=lambda item: (-item["total_count"], item["tool_name"]))

    total_tool_calls = total_tool_success + total_tool_error
    tool_success_rate = round((total_tool_success / total_tool_calls) * 100, 1) if total_tool_calls > 0 else 0.0

    return {
        "active_websocket_connections": active_ws,
        "celery_queue_depth": celery_depth,
        "tokens": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "by_model": model_breakdown,
        },
        "prompt_cache": {
            "hits": cache_hits,
            "misses": cache_misses,
            "total_lookups": total_lookups,
            "hit_rate_percent": cache_hit_rate,
        },
        "ttft": {
            "total_observations": ttft_total_count,
            "avg_ms": ttft_avg_ms,
            "buckets": ttft_buckets,
        },
        "tools": {
            "registered_count": len(registered_meta),
            "total_calls": total_tool_calls,
            "success_calls": total_tool_success,
            "error_calls": total_tool_error,
            "success_rate_percent": tool_success_rate,
            "by_tool": tool_stats,
            "recent_audits": get_recent_tool_audits(limit=audit_limit),
        },
        "cognitive": get_cognitive_telemetry_snapshot(limit=audit_limit),
    }


def _collect_business_and_sla_stats(db: Session, ticket_limit: int) -> Dict[str, Any]:
    """Aggregates ChatSession, ChatMessage, Approval, and P0-P4 Ticket SLA compliance from ORM."""
    active_sessions = int(
        db.query(func.count(ChatSession.id)).filter(ChatSession.is_deleted == False).scalar() or 0  # noqa: E712
    )
    total_sessions = int(db.query(func.count(ChatSession.id)).scalar() or 0)
    total_messages = int(db.query(func.count(ChatMessage.id)).scalar() or 0)
    user_messages = int(db.query(func.count(ChatMessage.id)).filter(ChatMessage.role == "user").scalar() or 0)
    assistant_messages = int(db.query(func.count(ChatMessage.id)).filter(ChatMessage.role == "assistant").scalar() or 0)
    avg_thinking_raw = db.query(func.avg(ChatMessage.duration_seconds)).filter(
        ChatMessage.duration_seconds.isnot(None)
    ).scalar()
    avg_thinking_seconds = round(float(avg_thinking_raw or 0.0), 2)

    pending_approvals = int(db.query(func.count(Approval.id)).filter(Approval.status == "PENDING").scalar() or 0)
    approved_approvals = int(db.query(func.count(Approval.id)).filter(Approval.status == "APPROVED").scalar() or 0)
    rejected_approvals = int(db.query(func.count(Approval.id)).filter(Approval.status == "REJECTED").scalar() or 0)
    total_approvals = int(db.query(func.count(Approval.id)).scalar() or 0)
    closed_approvals = approved_approvals + rejected_approvals
    approval_closure_rate = round((closed_approvals / total_approvals) * 100, 1) if total_approvals > 0 else 0.0

    # Ticket & P0-P4 SLA Aggregation
    now_utc = datetime.utcnow()
    tickets = db.query(Ticket).order_by(Ticket.created_at.desc(), Ticket.id.desc()).all()

    tier_accum: Dict[str, Dict[str, int]] = {
        p: {"total": 0, "open": 0, "closed": 0, "within_sla": 0, "breached": 0}
        for p in PRIORITY_ORDER
    }
    recent_tickets: List[Dict[str, Any]] = []
    total_within_sla = 0
    total_open_tickets = 0
    total_closed_tickets = 0
    total_breached_tickets = 0

    for idx, t in enumerate(tickets):
        p_code = str(t.priority or "P3").upper()
        if p_code not in PRIORITY_META:
            p_code = "P3"

        status_upper = str(t.status or "OPEN").upper()
        is_closed = status_upper in CLOSED_TICKET_STATUSES

        created_naive = (
            t.created_at.astimezone(timezone.utc).replace(tzinfo=None)
            if t.created_at and t.created_at.tzinfo is not None
            else (t.created_at or now_utc)
        )
        age_minutes = max(0.0, (now_utc - created_naive).total_seconds() / 60.0)
        limit_minutes = int(PRIORITY_META[p_code]["limit_minutes"])

        within_sla = True if is_closed else (age_minutes <= limit_minutes)
        if is_closed:
            sla_state = "已闭环"
            total_closed_tickets += 1
            tier_accum[p_code]["closed"] += 1
        elif within_sla:
            sla_state = "履约中"
            total_open_tickets += 1
            tier_accum[p_code]["open"] += 1
        else:
            sla_state = "已超期"
            total_open_tickets += 1
            tier_accum[p_code]["open"] += 1

        tier_accum[p_code]["total"] += 1
        if within_sla:
            total_within_sla += 1
            tier_accum[p_code]["within_sla"] += 1
        else:
            total_breached_tickets += 1
            tier_accum[p_code]["breached"] += 1

        if idx < ticket_limit:
            sla_baseline = SLA_METRICS.get(p_code, SLA_METRICS["P3"])
            recent_tickets.append(
                {
                    "ticket_id": t.ticket_id,
                    "title": t.title,
                    "priority": p_code,
                    "department": t.department,
                    "status": status_upper,
                    "response_sla": t.response_sla or sla_baseline["response_sla"],
                    "resolution_sla": t.resolution_sla or sla_baseline["resolution_sla"],
                    "action_taken": t.action_taken or sla_baseline["action"],
                    "sla_state": sla_state,
                    "within_sla": within_sla,
                    "age_minutes": round(age_minutes, 1),
                    "created_at": created_naive.replace(tzinfo=timezone.utc).isoformat(),
                }
            )

    sla_tiers: List[Dict[str, Any]] = []
    for p_code in PRIORITY_ORDER:
        acc = tier_accum[p_code]
        baseline = SLA_METRICS[p_code]
        meta = PRIORITY_META[p_code]
        t_total = acc["total"]
        compliance = round((acc["within_sla"] / t_total) * 100, 1) if t_total > 0 else 100.0
        sla_tiers.append(
            {
                "priority": p_code,
                "level_label": meta["label"],
                "response_sla": baseline["response_sla"],
                "resolution_sla": baseline["resolution_sla"],
                "action_policy": baseline["action"],
                "resolution_limit_minutes": meta["limit_minutes"],
                "total_count": t_total,
                "open_count": acc["open"],
                "closed_count": acc["closed"],
                "within_sla_count": acc["within_sla"],
                "breached_count": acc["breached"],
                "has_tickets": t_total > 0,
                "compliance_rate_percent": compliance,
            }
        )

    total_tickets = len(tickets)
    overall_sla_compliance = round((total_within_sla / total_tickets) * 100, 1) if total_tickets > 0 else 100.0

    return {
        "chat": {
            "active_sessions": active_sessions,
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "user_messages": user_messages,
            "assistant_messages": assistant_messages,
            "avg_thinking_seconds": avg_thinking_seconds,
        },
        "approvals": {
            "pending_count": pending_approvals,
            "approved_count": approved_approvals,
            "rejected_count": rejected_approvals,
            "closed_count": closed_approvals,
            "total_count": total_approvals,
            "closure_rate_percent": approval_closure_rate,
        },
        "sla": {
            "total_tickets": total_tickets,
            "open_tickets": total_open_tickets,
            "closed_tickets": total_closed_tickets,
            "breached_tickets": total_breached_tickets,
            "overall_compliance_percent": overall_sla_compliance,
            "tiers": sla_tiers,
            "recent_tickets": recent_tickets,
        },
    }


@router.get("/overview", response_model=StandardResponse)
async def get_monitoring_overview(
    audit_limit: int = Query(20, ge=1, le=100, description="近期工具调用审计返回条数"),
    ticket_limit: int = Query(20, ge=1, le=100, description="近期企业工单台账返回条数"),
    db: Session = Depends(get_db),
    current_user: UserPayload = Depends(require_role([RoleEnum.ADMIN])),
) -> StandardResponse:
    """Returns structured real-time system health, Prometheus telemetry, tool audits, and P0-P4 SLA stats."""
    mysql_ok = check_mysql_health()
    redis_ok = await check_redis_health()
    qdrant_ok = check_qdrant_health()
    qdrant_info = get_qdrant_info()
    llm_info = get_llm_info()
    sanitized_cfg = get_sanitized_admin_config()

    bind = db.get_bind()
    db_dialect = str(getattr(getattr(bind, "dialect", None), "name", "sqlite"))

    task_records = list_task_records(limit=80)
    active_ingestion_tasks = sum(
        1 for t in task_records if str(t.get("status", "")).upper() in ACTIVE_TASK_STATUSES
    )

    telemetry = _collect_prometheus_snapshot(audit_limit=audit_limit)
    business = _collect_business_and_sla_stats(db=db, ticket_limit=ticket_limit)

    all_core_up = mysql_ok and redis_ok and qdrant_ok
    overall_status = "HEALTHY" if all_core_up else "DEGRADED"

    components = [
        {
            "key": "database",
            "name": "关系型数据库",
            "status": "UP" if mysql_ok else "DOWN",
            "mode": db_dialect,
            "detail": f"连接池正常 ({db_dialect})" if mysql_ok else "数据库连接异常",
        },
        {
            "key": "redis",
            "name": "Redis 缓存与队列",
            "status": "UP" if redis_ok else "DOWN",
            "mode": "standalone" if redis_ok else "local_fallback",
            "detail": "分布式缓存与队列就绪" if redis_ok else "Redis 离线，运行于内存降级模式",
        },
        {
            "key": "qdrant",
            "name": "Qdrant 向量知识库",
            "status": "UP" if qdrant_ok else "DOWN",
            "mode": str(qdrant_info.get("client_mode") or "local_storage"),
            "detail": f"{qdrant_info.get('points_count', 0)} 索引切片 · {qdrant_info.get('vector_size', 1024)} 维",
        },
        {
            "key": "llm_engine",
            "name": "大模型推理引擎",
            "status": "READY",
            "mode": str(llm_info.get("active_engine") or llm_info.get("provider") or "auto"),
            "detail": f"{llm_info.get('model')} · {'深度思考' if llm_info.get('thinking') else '极速模式'}",
        },
    ]

    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "operator": {
            "username": current_user.username,
            "display_name": current_user.display_name,
            "role": current_user.role.value,
            "department": current_user.department,
        },
        "system_health": {
            "overall_status": overall_status,
            "components": components,
            "llm_engine": {
                "provider": llm_info.get("provider"),
                "model": llm_info.get("model"),
                "active_engine": llm_info.get("active_engine"),
                "thinking": bool(llm_info.get("thinking")),
                "has_api_key": bool(llm_info.get("has_api_key")),
                "api_key_masked": sanitized_cfg.get("api_key_masked", ""),
                "endpoint": llm_info.get("api_base"),
            },
            "qdrant": {
                "status": qdrant_info.get("status"),
                "client_mode": qdrant_info.get("client_mode"),
                "collection_name": qdrant_info.get("collection_name"),
                "points_count": int(qdrant_info.get("points_count") or 0),
                "vector_size": int(qdrant_info.get("vector_size") or 1024),
            },
            "active_ingestion_tasks": active_ingestion_tasks,
        },
        "telemetry": telemetry,
        "business": business,
    }

    return StandardResponse(
        code=200,
        message="系统遥测、工具审计与 SLA 监控全景已加载",
        data=data,
    )
