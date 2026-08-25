"""MySQL Database Engine & Session Manager with Read/Write Splitting Routing."""

import logging
from typing import Generator, Optional
from sqlalchemy import create_engine, text, Engine
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from backend.core.config import settings

logger = logging.getLogger("database")


# 1. Base Declarative Class
class Base(DeclarativeBase):
    pass


# 2. Master & Replica Engines Configuration with High-Concurrency Connection Pooling
# Pool configuration: pool_size=100, max_overflow=50, pool_pre_ping=True
master_uri = getattr(settings, "SQLALCHEMY_MASTER_DATABASE_URI", settings.SQLALCHEMY_DATABASE_URI)
replica_uri = getattr(settings, "SQLALCHEMY_REPLICA_DATABASE_URI", settings.SQLALCHEMY_DATABASE_URI)

master_engine: Engine = create_engine(
    master_uri,
    pool_pre_ping=True,
    pool_size=100,
    max_overflow=50,
    echo=False,
)

replica_engine: Engine = create_engine(
    replica_uri,
    pool_pre_ping=True,
    pool_size=100,
    max_overflow=50,
    echo=False,
)

# Fallback / Default engine pointer
engine = master_engine


class RoutingSession(Session):
    """
    Custom SQLAlchemy Session that routes SQL operations:
    - Write operations (INSERT, UPDATE, DELETE) & flushed changes -> Master Engine
    - Read operations (SELECT queries) without dirty objects -> Replica Engine
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._force_master = False

    def get_bind(self, mapper=None, clause=None, bind=None, **kw):
        # 1. If explicit bind is provided, respect it
        if bind is not None:
            return bind

        # 2. If explicit master forced, flushing, or has modified objects -> Master
        if self._force_master or self._flushing or len(self.new) > 0 or len(self.dirty) > 0 or len(self.deleted) > 0:
            return master_engine

        # 3. If clause is an executable SQL statement, route based on statement type
        if clause is not None:
            stmt_text = str(clause).strip().upper()
            if stmt_text.startswith(("INSERT", "UPDATE", "DELETE", "ALTER", "DROP", "CREATE", "REPLACE")):
                return master_engine
            return replica_engine

        # 4. Default read routing to replica engine
        return replica_engine


# Session factory bound to RoutingSession
RoutingSessionLocal = sessionmaker(
    class_=RoutingSession,
    autocommit=False,
    autoflush=False,
)


def get_db() -> Generator[Session, None, None]:
    """Dependency generator for FastAPI routes yielding a RoutingSession."""
    db = RoutingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_mysql_health(target_engine: Optional[Engine] = None) -> bool:
    """Checks MySQL connectivity against master or replica."""
    eng = target_engine or master_engine
    try:
        with eng.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.warning(f"MySQL health check failed on {eng}: {e}")
        return False
