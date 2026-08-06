"""FastAPI Celery Asynchronous Task Status & Query Endpoints."""

from typing import Dict, Any
from fastapi import APIRouter, Depends, Path
from celery.result import AsyncResult
from backend.core.exceptions import StandardResponse
from backend.core.rbac import require_role, RoleEnum, UserPayload
from backend.tasks.celery_app import celery_app

router = APIRouter(prefix="", tags=["Async Tasks"])


@router.get("/{task_id}/status", response_model=StandardResponse)
async def get_task_status(
    task_id: str = Path(..., description="Celery Task ID string"),
    current_user: UserPayload = Depends(require_role([RoleEnum.ADMIN, RoleEnum.MANAGER, RoleEnum.EMPLOYEE]))
):
    """
    Queries current execution status, progress, and result of a Celery async task.
    """
    task_result = AsyncResult(task_id, app=celery_app)
    state = task_result.state

    response_data: Dict[str, Any] = {
        "task_id": task_id,
        "status": state,
        "ready": task_result.ready(),
        "successful": task_result.successful() if task_result.ready() else False,
    }

    if state == "PENDING":
        response_data["message"] = "Task is pending execution"
        response_data["progress"] = {"current": 0, "total": 100}
    elif state == "PROGRESS":
        info = task_result.info or {}
        response_data["message"] = info.get("status", "Task is in progress")
        response_data["progress"] = {
            "current": info.get("current", 50),
            "total": info.get("total", 100)
        }
        response_data["meta"] = info
    elif state == "SUCCESS":
        result = task_result.result
        response_data["message"] = "Task completed successfully"
        response_data["progress"] = {"current": 100, "total": 100}
        response_data["result"] = result
    elif state == "FAILURE":
        response_data["message"] = f"Task execution failed: {str(task_result.info)}"
        response_data["error"] = str(task_result.info)
    else:
        response_data["message"] = f"Task state: {state}"
        response_data["meta"] = str(task_result.info)

    return StandardResponse(
        code=200,
        message=f"Task '{task_id}' status retrieved",
        data=response_data
    )
