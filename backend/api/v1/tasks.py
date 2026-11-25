"""FastAPI Admin Asynchronous & Ingestion Task Status Query Endpoints."""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, Path, Query

from backend.core.exceptions import StandardResponse
from backend.core.knowledge_ledger import (
    build_pipeline_steps,
    get_task_record,
    infer_stage_from_state,
    list_task_records,
    update_task_record,
)
from backend.core.rbac import RoleEnum, UserPayload, require_role
from backend.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["Async Tasks"])


def _query_celery_result_safely(
    task_id: str,
    ledger_record: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Queries Celery AsyncResult without crashing when Redis result backend is offline."""
    try:
        task_result = AsyncResult(task_id, app=celery_app)
        state = str(task_result.state or "PENDING")
        ready = bool(task_result.ready())
        successful = bool(task_result.successful()) if ready else False
        info_raw = task_result.info
        info_dict = info_raw if isinstance(info_raw, dict) else {}

        stage, stage_label, pct = infer_stage_from_state(state, info_dict)
        response_data: Dict[str, Any] = {
            "task_id": task_id,
            "status": state,
            "stage": stage,
            "stage_label": stage_label,
            "ready": ready,
            "successful": successful,
            "progress": {"current": pct, "total": 100},
            "steps": build_pipeline_steps(stage, state),
        }

        if state == "PENDING":
            response_data["message"] = "任务排队等待执行中"
            response_data["progress"] = {"current": 0, "total": 100}
        elif state == "PROGRESS":
            response_data["message"] = str(info_dict.get("status") or stage_label)
            response_data["progress"] = {
                "current": int(info_dict.get("current", 50) or 50),
                "total": int(info_dict.get("total", 100) or 100),
            }
            response_data["meta"] = info_dict
        elif state == "SUCCESS":
            result = task_result.result
            response_data["message"] = "任务解析与向量入库已完成"
            response_data["progress"] = {"current": 100, "total": 100}
            response_data["result"] = result
            if ledger_record and ledger_record.get("status") != "SUCCESS":
                update_task_record(
                    task_id,
                    status="SUCCESS",
                    stage="COMPLETED",
                    progress_current=100,
                    message=response_data["message"],
                    result=result if isinstance(result, dict) else None,
                )
        elif state == "FAILURE":
            err_msg = str(info_raw)
            response_data["message"] = f"任务执行失败: {err_msg}"
            response_data["error"] = err_msg
            if ledger_record and ledger_record.get("status") != "FAILURE":
                update_task_record(
                    task_id,
                    status="FAILURE",
                    stage="FAILED",
                    message=response_data["message"],
                    error=err_msg,
                )
        else:
            response_data["message"] = f"任务状态: {state}"
            response_data["meta"] = str(info_raw)

        if ledger_record:
            for meta_key in (
                "task_type",
                "filename",
                "filepath",
                "size_bytes",
                "category",
                "execution_mode",
                "fallback_reason",
                "uploader",
                "created_at",
                "updated_at",
            ):
                if meta_key in ledger_record and meta_key not in response_data:
                    response_data[meta_key] = ledger_record[meta_key]

        return response_data
    except Exception as exc:
        logger.debug("Celery AsyncResult lookup unavailable for %s: %s", task_id, exc)
        return None


def _resolve_task_status_payload(task_id: str) -> Dict[str, Any]:
    """Resolves unified task status from local ledger and/or Celery AsyncResult."""
    ledger_record = get_task_record(task_id)

    if ledger_record and ledger_record.get("execution_mode") in ("sync", "sync_rebuild", "async_fallback"):
        return ledger_record

    celery_payload = _query_celery_result_safely(task_id, ledger_record=ledger_record)
    if celery_payload is not None:
        celery_status = str(celery_payload.get("status") or "").upper()
        ledger_status = str(ledger_record.get("status") or "").upper() if ledger_record else ""
        if ledger_record and (
            (celery_status == "PENDING" and ledger_status in ("PROGRESS", "SUCCESS", "FAILURE"))
            or (
                celery_status in ("PENDING", "PROGRESS", "STARTED", "RETRY")
                and ledger_status in ("SUCCESS", "FAILURE")
            )
        ):
            return ledger_record
        return celery_payload

    if ledger_record is not None:
        return ledger_record

    return {
        "task_id": task_id,
        "status": "PENDING",
        "stage": "QUEUED",
        "stage_label": "任务等待中或结果后端暂不可达",
        "ready": False,
        "successful": False,
        "progress": {"current": 0, "total": 100},
        "message": "任务等待调度中（若 Celery Broker 未启动，请在上传时启用自动降级模式）",
        "steps": build_pipeline_steps("QUEUED", "PENDING"),
    }


def _collect_tasks_overview(limit: int) -> Dict[str, Any]:
    """Lists recent ingestion/sync tasks with refreshed status and summary counts."""
    raw_items = list_task_records(limit=limit)
    resolved_items: List[Dict[str, Any]] = []
    for item in raw_items:
        mode = item.get("execution_mode")
        if mode in ("celery_worker", "celery_eager") and not item.get("ready"):
            resolved_items.append(_resolve_task_status_payload(str(item["task_id"])))
        else:
            resolved_items.append(item)

    running_cnt = sum(1 for t in resolved_items if t.get("status") in ("PENDING", "PROGRESS", "STARTED", "RETRY"))
    completed_cnt = sum(1 for t in resolved_items if t.get("status") == "SUCCESS")
    failed_cnt = sum(1 for t in resolved_items if t.get("status") == "FAILURE")

    return {
        "tasks": resolved_items,
        "summary": {
            "total": len(resolved_items),
            "running": running_cnt,
            "completed": completed_cnt,
            "failed": failed_cnt,
        },
        "celery_eager_mode": bool(getattr(celery_app.conf, "task_always_eager", False)),
    }


@router.get("", response_model=StandardResponse)
async def list_tasks(
    limit: int = Query(30, ge=1, le=100, description="Maximum number of recent tasks to return"),
    current_user: UserPayload = Depends(require_role([RoleEnum.ADMIN])),
):
    """Admin-only endpoint listing recent document ingestion and knowledge base sync tasks."""
    overview = await asyncio.to_thread(_collect_tasks_overview, limit)
    return StandardResponse(
        code=200,
        message="Tasks ledger retrieved successfully",
        data=overview,
    )


@router.get("/{task_id}/status", response_model=StandardResponse)
async def get_task_status(
    task_id: str = Path(..., description="Task ID string (Celery UUID or local ledger ID)"),
    current_user: UserPayload = Depends(require_role([RoleEnum.ADMIN])),
):
    """Admin-only endpoint querying execution stage, progress, and outcome of an async or sync task."""
    response_data = await asyncio.to_thread(_resolve_task_status_payload, task_id)
    return StandardResponse(
        code=200,
        message=f"Task '{task_id}' status retrieved",
        data=response_data,
    )
