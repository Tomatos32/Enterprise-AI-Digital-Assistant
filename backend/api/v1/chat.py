"""Chat Management, Session Persistence & Three-Layer Abort Control REST API Router."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from backend.core.task_manager import task_manager
from backend.db.session import get_db
from backend.graph.workflow import graph
from backend.models.chat import ChatMessage, ChatSession

router = APIRouter()


# ---------------------------------------------------------
# Pydantic Request / Response Schemas
# ---------------------------------------------------------
class ChatAbortRequest(BaseModel):
    thread_id: str = Field(..., description="会话线程 ID (如 thread_001)")


class SessionCreateRequest(BaseModel):
    title: Optional[str] = Field("新对话", description="会话标题")
    user_id: Optional[str] = Field("u_ws_default", description="所属用户 ID")


class SessionTitleUpdateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="新会话标题")


class ChatSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: str
    user_id: str
    title: str
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: str
    role: str
    content: str
    sources: Optional[str] = None
    created_at: datetime


# ---------------------------------------------------------
# REST Endpoints
# ---------------------------------------------------------
@router.post("/sessions", response_model=ChatSessionResponse, tags=["Chat Sessions"])
async def create_chat_session(
    req: SessionCreateRequest,
    db: Session = Depends(get_db),
):
    """Creates a new persistent chat session."""
    new_session_id = f"sess_{uuid.uuid4().hex[:12]}"
    session = ChatSession(
        session_id=new_session_id,
        user_id=req.user_id or "u_ws_default",
        title=req.title or "新对话",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/sessions", response_model=List[ChatSessionResponse], tags=["Chat Sessions"])
async def list_chat_sessions(
    user_id: str = Query("u_ws_default", description="用户 ID 过滤"),
    limit: int = Query(50, ge=1, le=100, description="返回数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    db: Session = Depends(get_db),
):
    """Lists active (non-deleted) chat sessions for the specified user ordered by last updated."""
    query = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user_id, ChatSession.is_deleted == False)  # noqa: E712
        .order_by(ChatSession.updated_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return query.all()


@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageResponse], tags=["Chat Sessions"])
async def get_session_messages(
    session_id: str,
    db: Session = Depends(get_db),
):
    """Retrieves all chat messages for a specific session ordered by creation time."""
    # Ensure session exists and not deleted
    session = (
        db.query(ChatSession)
        .filter(ChatSession.session_id == session_id, ChatSession.is_deleted == False)  # noqa: E712
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail=f"Chat session '{session_id}' not found or has been deleted.")

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return messages


@router.put("/sessions/{session_id}/title", response_model=ChatSessionResponse, tags=["Chat Sessions"])
async def update_session_title(
    session_id: str,
    req: SessionTitleUpdateRequest,
    db: Session = Depends(get_db),
):
    """Renames an existing chat session."""
    session = (
        db.query(ChatSession)
        .filter(ChatSession.session_id == session_id, ChatSession.is_deleted == False)  # noqa: E712
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail=f"Chat session '{session_id}' not found.")

    session.title = req.title.strip()
    session.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(session)
    return session


@router.delete("/sessions/{session_id}", tags=["Chat Sessions"])
async def delete_chat_session(
    session_id: str,
    db: Session = Depends(get_db),
):
    """Soft-deletes a chat session so it no longer appears in active history."""
    session = (
        db.query(ChatSession)
        .filter(ChatSession.session_id == session_id, ChatSession.is_deleted == False)  # noqa: E712
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail=f"Chat session '{session_id}' not found.")

    session.is_deleted = True
    session.updated_at = datetime.utcnow()
    db.commit()
    return {"status": "SUCCESS", "message": f"Session '{session_id}' successfully deleted."}


@router.post("/abort", tags=["Chat Control"])
async def abort_chat_generation(
    req: ChatAbortRequest,
) -> Dict[str, Any]:
    """Three-Layer AI Abort API:

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
        "message": f"会话线程 '{req.thread_id}' 已物理成功中断，更新快照为 CANCELLED",
    }
