"""SQLAlchemy 2.0 Database Session Manager."""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from backend.core.config import settings

# 1. SQLAlchemy Engine & Session Local
engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# 2. Base Model Class
class Base(DeclarativeBase):
    pass


def get_db():
    """
    Dependency generator for DB sessions.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_mysql_health() -> bool:
    """
    Checks MySQL connectivity.
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
