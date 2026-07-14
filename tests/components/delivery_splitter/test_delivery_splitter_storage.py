# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from profed.components.delivery_splitter.storage import _Storage


AT = datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)


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
async def test_accept_edge_upserts_and_clears_deleted(store, fake_conn):
    await store.accept_edge("alice@example.com", "bob@remote.example", AT)
    fake_conn.execute.assert_awaited_once()
    sql, *args = fake_conn.execute.call_args[0]
    assert "INSERT" in sql and "ON CONFLICT" in sql and "tstzrange" in sql
    assert args == ["alice@example.com", "bob@remote.example", AT]


@pytest.mark.asyncio
async def test_delete_edge_sets_deleted_at(store, fake_conn):
    await store.delete_edge("alice@example.com", "bob@remote.example", AT)
    fake_conn.execute.assert_awaited_once()
    sql, *args = fake_conn.execute.call_args[0]
    assert "UPDATE" in sql and "tstzrange(lower(valid), $3)" in sql
    assert args == ["alice@example.com", "bob@remote.example", AT]


@pytest.mark.asyncio
async def test_recipients_at_queries_open_edges(store, fake_conn):
    fake_conn.fetch.return_value = [{"follower": "bob@remote.example"},
                                    {"follower": "carol@remote.example"}]
    result = await store.recipients_at("alice@example.com", AT)
    assert result == {"bob@remote.example", "carol@remote.example"}
    sql, *args = fake_conn.fetch.call_args[0]
    assert "valid @> $2" in sql
    assert args == ["alice@example.com", AT]


@pytest.mark.asyncio
async def test_recipients_at_empty(store, fake_conn):
    fake_conn.fetch.return_value = []
    assert await store.recipients_at("alice@example.com", AT) == set()

