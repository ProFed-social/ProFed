# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from profed.components.delivery_distributor.storage import _Storage


AT = datetime(2026, 4, 1, tzinfo=timezone.utc)


@pytest.fixture
def fake_conn():
    conn = Mock()
    conn.execute = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    return conn


@pytest.fixture
def store(fake_conn):
    class _Ctx:
        def __init__(self, conn):
            self.conn = conn

        async def __aenter__(self):
            return self.conn

        async def __aexit__(self, *_):
            pass

    pool = Mock()
    pool.acquire = Mock(return_value=_Ctx(fake_conn))
    return _Storage(pool)


@pytest.mark.asyncio
async def test_enqueue_inserts_ignoring_conflict(store, fake_conn):
    await store.enqueue("bob@r", "https://x/1", 42, "alice", {"type": "Create"})
    sql, *args = fake_conn.execute.call_args[0]
    assert "INSERT" in sql and "ON CONFLICT (recipient, activity_id) DO NOTHING" in sql
    assert args == ["bob@r", "https://x/1", 42, "alice", {"type": "Create"}]


@pytest.mark.asyncio
async def test_mark_attempting_sets_attempt_and_clears_failed(store, fake_conn):
    await store.mark_attempting("bob@r", "https://x/1", 2, AT)
    sql, *args = fake_conn.execute.call_args[0]
    assert "UPDATE" in sql and "failed_at        = NULL" in sql and "COALESCE(first_attempt_at" in sql
    assert args == ["bob@r", "https://x/1", 2, AT]


@pytest.mark.asyncio
async def test_mark_failed_sets_failed_at(store, fake_conn):
    await store.mark_failed("bob@r", "https://x/1", AT)
    sql, *args = fake_conn.execute.call_args[0]
    assert "UPDATE" in sql and "failed_at = $3" in sql
    assert args == ["bob@r", "https://x/1", AT]


@pytest.mark.asyncio
async def test_dequeue_deletes(store, fake_conn):
    await store.dequeue("bob@r", "https://x/1")
    sql, *args = fake_conn.execute.call_args[0]
    assert "DELETE" in sql
    assert args == ["bob@r", "https://x/1"]


@pytest.mark.asyncio
async def test_recipients_with_work_distinct(store, fake_conn):
    fake_conn.fetch.return_value = [{"recipient": "bob@r"}, {"recipient": "carol@r"}]
    assert await store.recipients_with_work() == {"bob@r", "carol@r"}
    assert "DISTINCT recipient" in fake_conn.fetch.call_args[0][0]


@pytest.mark.asyncio
async def test_head_orders_by_seq(store, fake_conn):
    fake_conn.fetchrow.return_value = {"activity_id": "https://x/1", "seq": 5,
                                       "username": "alice", "activity": {},
                                       "attempt": 0, "attempt_at": None,
                                       "failed_at": None, "first_attempt_at": None}
    result = await store.head("bob@r")
    assert result["seq"] == 5
    sql, *args = fake_conn.fetchrow.call_args[0]
    assert "ORDER BY seq" in sql and "LIMIT 1" in sql
    assert args == ["bob@r"]


@pytest.mark.asyncio
async def test_upsert_user_key(store, fake_conn):
    await store.upsert_user_key("alice", "PUB", "PRIV")
    sql, *args = fake_conn.execute.call_args[0]
    assert "INSERT INTO delivery_distributor.user_keys" in sql and "ON CONFLICT" in sql
    assert args == ["alice", "PUB", "PRIV"]


@pytest.mark.asyncio
async def test_get_user_key_returns_tuple(store, fake_conn):
    fake_conn.fetchrow.return_value = {"public_key_pem": "PUB", "private_key_pem": "PRIV"}
    assert await store.get_user_key("alice") == ("PUB", "PRIV")


@pytest.mark.asyncio
async def test_get_user_key_missing_returns_none(store, fake_conn):
    fake_conn.fetchrow.return_value = None
    assert await store.get_user_key("nobody") is None

