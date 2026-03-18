# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, Mock
from profed.components.api.storage import actor


@pytest.fixture
def fake_conn():
    conn = Mock()
    conn.execute = AsyncMock()
    conn.fetchrow = AsyncMock()
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

    backup = actor._instance
    actor._instance = actor._storage(pool, "test_schema")

    yield pool

    actor._instance = backup



@pytest.mark.asyncio
async def test_add_actor(fake_pool):
    store = await actor.storage()
    await store.add("alice", {"name": "Alice"})

    async with fake_pool.acquire() as conn:
        conn.execute.assert_called_once()


@pytest.mark.asyncio
async def test_update_actor(fake_pool):
    store = await actor.storage()
    await store.update("alice", {"name": "Alice Updated"})

    async with fake_pool.acquire() as conn:
        conn.execute.assert_called_once()


@pytest.mark.asyncio
async def test_delete_actor(fake_pool):
    store = await actor.storage()
    await store.delete("alice")

    async with fake_pool.acquire() as conn:
        conn.execute.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_actor_found(fake_pool):
    store = await actor.storage()
    await store.delete("alice")

    async with fake_pool.acquire() as conn:
        conn.fetchrow.return_value = {"payload": {"name": "Alice"}}
        result = await store.fetch("alice")
        assert result is not None
        assert result["name"] == "Alice"


@pytest.mark.asyncio
async def test_fetch_actor_not_found(fake_pool):
    store = await actor.storage()
    await store.delete("alice")

    async with fake_pool.acquire() as conn:
        conn.fetchrow.return_value = None
        result = await store.fetch("alice")
        assert result is None
