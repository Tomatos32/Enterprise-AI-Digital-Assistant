"""Ticket SQLAlchemy ORM Model."""

from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from backend.db.session import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    ticket_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default="P3")
    department: Mapped[str] = mapped_column(String(50), default="IT")
    status: Mapped[str] = mapped_column(String(20), default="OPEN")
    response_sla: Mapped[str] = mapped_column(String(50), nullable=True)
    resolution_sla: Mapped[str] = mapped_column(String(50), nullable=True)
    action_taken: Mapped[str] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
