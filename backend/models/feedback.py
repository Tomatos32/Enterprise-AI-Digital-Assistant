"""SQLAlchemy Model for Human Feedback (RLHF / DPO)."""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Integer, String, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from backend.db.session import Base


class FeedbackRecord(Base):
    """
    Records explicit user ratings (like=1, dislike=-1), user corrections,
    and runtime context snapshots for continuous DPO/RLHF alignment.
    """
    __tablename__ = "feedback_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    thread_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    message_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 = like, -1 = dislike
    user_correction: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    context_snapshot: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
