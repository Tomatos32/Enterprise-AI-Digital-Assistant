"""Inventory SQLAlchemy ORM Model."""

from sqlalchemy import String, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column
from backend.db.session import Base


class Inventory(Base):
    __tablename__ = "inventories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    item_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    item_name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    spec: Mapped[str] = mapped_column(String(200), nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    stock: Mapped[int] = mapped_column(Integer, nullable=False)
    department: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="In Stock")
