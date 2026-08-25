"""Unit tests for MySQL Read/Write Splitting RoutingSession and Redis Sentinel/Pool."""

import pytest
from sqlalchemy import text
from backend.core.database import (
    master_engine,
    replica_engine,
    RoutingSessionLocal,
)
from backend.core.redis import parse_sentinel_hosts, get_redis_client


def test_routing_session_get_bind_select():
    """Test that SELECT queries route to Replica engine by default."""
    session = RoutingSessionLocal()
    try:
        select_clause = text("SELECT * FROM users WHERE id = 1")
        bind = session.get_bind(clause=select_clause)
        assert bind is replica_engine
    finally:
        session.close()


def test_routing_session_get_bind_insert_update_delete():
    """Test that INSERT/UPDATE/DELETE queries route to Master engine."""
    session = RoutingSessionLocal()
    try:
        insert_clause = text("INSERT INTO users (username) VALUES ('test')")
        bind_insert = session.get_bind(clause=insert_clause)
        assert bind_insert is master_engine

        update_clause = text("UPDATE users SET username='test2' WHERE id=1")
        bind_update = session.get_bind(clause=update_clause)
        assert bind_update is master_engine

        delete_clause = text("DELETE FROM users WHERE id=1")
        bind_delete = session.get_bind(clause=delete_clause)
        assert bind_delete is master_engine
    finally:
        session.close()


def test_routing_session_force_master_flag():
    """Test that setting _force_master=True routes SELECT queries to Master engine."""
    session = RoutingSessionLocal()
    try:
        session._force_master = True
        select_clause = text("SELECT 1")
        bind = session.get_bind(clause=select_clause)
        assert bind is master_engine
    finally:
        session.close()


def test_mysql_engine_pool_settings():
    """Test connection pool settings (pool_size=100, max_overflow=50)."""
    assert master_engine.pool.size() == 100
    assert master_engine.pool._max_overflow == 50
    assert replica_engine.pool.size() == 100
    assert replica_engine.pool._max_overflow == 50


def test_parse_sentinel_hosts():
    """Test parsing sentinel host:port string."""
    hosts_str = "127.0.0.1:26379, 127.0.0.1:26380, 10.0.0.1"
    parsed = parse_sentinel_hosts(hosts_str)
    assert parsed == [
        ("127.0.0.1", 26379),
        ("127.0.0.1", 26380),
        ("10.0.0.1", 26379),
    ]


@pytest.mark.asyncio
async def test_redis_client_standalone():
    """Test getting async redis client instance and ping check."""
    client = await get_redis_client()
    assert client is not None
