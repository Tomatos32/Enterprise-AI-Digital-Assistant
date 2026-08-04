"""Chat Management & Three-Layer Abort Control REST API Router."""

from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel, Field
from backend.core.task_manager import task_manager
from backend.graph.workflow import graph

router = APIRouter()


class ChatAbortRequest(BaseModel):
    thread_id: str = Field(..., description="会话线程 ID (如 thread_001)")


@router.post("/abort")
async def abort_chat_generation(
    req: ChatAbortRequest
) -> Dict[str, Any]:
    """
    Three-Layer AI Abort API:
    1. Cancels active running asyncio Task for thread_id.
    2. Updates LangGraph Checkpointer state metadata to status='CANCELLED'.
    """
    # 1. Cancel active running asyncio Task (Layer 2 Cancellation)
    task_cancelled = task_manager.abort_task(req.thread_id)

    # 2. Update Checkpointer State Metadata with status='CANCELLED' (Layer 3 Checkpoint Preservation)
    config = {"configurable": {"thread_id": req.thread_id}}
    snapshot_saved = False
    try:
        state_snapshot = graph.get_state(config)
        if state_snapshot and state_snapshot.values:
            meta = (state_snapshot.values.get("metadata") or {}).copy()
            meta["status"] = "CANCELLED"
            meta["aborted_at"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            graph.update_state(config, {"metadata": meta})
            snapshot_saved = True
    except Exception:
        pass

    return {
        "status": "SUCCESS",
        "thread_id": req.thread_id,
        "task_cancelled": task_cancelled,
        "checkpointer_snapshot_saved": snapshot_saved,
        "message": f"会话线程 '{req.thread_id}' 已物理成功中断，更新快照为 CANCELLED"
    }
