"""SQLAlchemy 2.0 Database Session Manager."""

import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from backend.core.config import settings

logger = logging.getLogger(__name__)


# 1. Base Model Class
class Base(DeclarativeBase):
    pass


def _create_db_engine():
    uri = settings.SQLALCHEMY_DATABASE_URI
    if "sqlite" in uri:
        eng = create_engine(uri, connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=eng)
        return eng

    # Try connecting to configured database
    try:
        eng = create_engine(
            uri,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20
        )
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        return eng
    except Exception as e:
        if settings.ENVIRONMENT in ("development", "test"):
            logger.warning(
                f"[Database] Target database unreachable ({e}). "
                "Falling back to local SQLite demo database ('sqlite:///./enterprise_ai_demo.db')."
            )
            fallback_eng = create_engine(
                "sqlite:///./enterprise_ai_demo.db",
                connect_args={"check_same_thread": False}
            )
            Base.metadata.create_all(bind=fallback_eng)
            try:
                from backend.db.seed import seed_initial_data
                with sessionmaker(bind=fallback_eng)() as s:
                    seed_initial_data(s)
            except Exception as seed_err:
                logger.warning(f"[Database] Seed warning: {seed_err}")
            return fallback_eng
        raise


engine = _create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


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
    Checks database connectivity.
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False

