"""Feedback API Router for collecting user thumbs-up/down & corrections."""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.db.session import get_db
from backend.models.feedback import FeedbackRecord

router = APIRouter()


class FeedbackCreateRequest(BaseModel):
    thread_id: str = Field(..., description="Conversation thread identifier")
    message_id: str = Field(..., description="Target message ID for this feedback")
    score: int = Field(..., ge=-1, le=1, description="Rating: 1 for like, -1 for dislike")
    user_correction: Optional[str] = Field(None, description="Optional user correction or revised prompt/answer")
    context_snapshot: Optional[Dict[str, Any]] = Field(None, description="Snapshot of prompt, LLM output, context")


class FeedbackResponse(BaseModel):
    id: int
    status: str
    message: str


@router.post("/feedback", response_model=FeedbackResponse, tags=["Human Feedback & DPO"])
async def submit_feedback(
    request: FeedbackCreateRequest,
    db: Session = Depends(get_db)
):
    """
    Submits user feedback (like/dislike & correction) into the database for DPO alignment.
    """
    if request.score not in (-1, 1):
        raise HTTPException(status_code=400, detail="Score must be either 1 (like) or -1 (dislike).")

    feedback = FeedbackRecord(
        thread_id=request.thread_id,
        message_id=request.message_id,
        score=request.score,
        user_correction=request.user_correction,
        context_snapshot=request.context_snapshot
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    return FeedbackResponse(
        id=feedback.id,
        status="success",
        message="Feedback successfully recorded for model alignment."
    )
