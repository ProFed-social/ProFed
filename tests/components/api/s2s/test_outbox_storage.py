# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, Mock
from profed.components.api.s2s.outbox import storage as outbox


@pytest.fixture
def fake_conn():
    conn = Mock()
    conn.execute = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    return conn


@pytest.fixture
def fake_pool(fake_conn):
    class AsyncContextManagerMock:
        def __init__(self, conn):
            self.conn = conn
        async def __aenter__(self):
            return self.conn
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    pool = Mock()
    pool.acquire = Mock(return_value=AsyncContextManagerMock(fake_conn))

    backup = outbox._instance
    outbox._instance = outbox._storage(pool)

    yield pool

    outbox._instance = backup


@pytest.mark.asyncio
async def test_ensure_table_success(fake_pool, fake_conn):
    store = await outbox.storage()
    await store.ensure_table()

    assert fake_conn.execute.await_count == 2


@pytest.mark.asyncio
async def test_add_success(fake_pool, fake_conn):
    store = await outbox.storage()

    activity = {
        "type": "Create",
        "actor": "https://example.com/actors/alice",
        "object": {"type": "Person", "id": "https://example.com/actors/alice"},
    }

    await store.add("alice", activity)

    fake_conn.execute.assert_awaited_with(
                               f"""INSERT INTO api.s2s_outbox (username, activity)
                                   VALUES ($1, $2)
                               """,
                               "alice",
                               activity)


@pytest.mark.asyncio
async def test_fetch_found(fake_pool, fake_conn):
    store = await outbox.storage()

    activity_1 = {
        "type": "Create",
        "actor": "https://example.com/actors/alice",
        "object": {"type": "Person", "id": "https://example.com/actors/alice"},
    }
    activity_2 = {
        "type": "Update",
        "actor": "https://example.com/actors/alice",
        "object": {"type": "Person", "id": "https://example.com/actors/alice"},
    }

    fake_conn.fetch.return_value = [
        {"activity": activity_1},
        {"activity": activity_2},
    ]

    result = await store.fetch("alice")

    fake_conn.fetch.assert_awaited_with(
                                    f"""SELECT activity
                                        FROM api.s2s_outbox
                                        WHERE username = $1
                                        ORDER BY created_at
                                    """,
                                    "alice")
    assert result == [activity_1, activity_2]


@pytest.mark.asyncio
async def test_fetch_not_found(fake_pool, fake_conn):
    store = await outbox.storage()

    fake_conn.fetch.return_value = []

    result = await store.fetch("alice")

    assert result == []


@pytest.mark.asyncio
async def test_outbox_storage_not_initialized():
    backup = outbox._instance
    outbox._instance = None

    try:
        with pytest.raises(RuntimeError):
            await outbox.storage()
    finally:
        outbox._instance = backup

