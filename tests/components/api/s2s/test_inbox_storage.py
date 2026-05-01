# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, Mock
from profed.components.api.s2s.inbox import storage


@pytest.fixture
def fake_conn():
    conn = AsyncMock()

    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value={})
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

    storage.reinit(pool)
    return pool


@pytest.mark.asyncio
async def test_add_user_success(fake_pool):
    store = await storage.storage()
    await store.add("alice")

    async with fake_pool.acquire() as conn:
        args = conn.execute.call_args[0]
        assert "s2s_inbox_users" in args[0]
        assert "INSERT" in args[0]
        assert args[1] == "alice"


@pytest.mark.asyncio
async def test_add_user_already_exists(fake_pool):
    store = await storage.storage()
    await store.add("alice")

    async with fake_pool.acquire() as conn:
        args = conn.execute.call_args[0]
        assert "s2s_inbox_users" in args[0]
        assert "INSERT" in args[0]
        assert args[1] == "alice"


@pytest.mark.asyncio
async def test_delete_user_success(fake_pool):
    store = await storage.storage()
    await store.delete("alice")

    async with fake_pool.acquire() as conn:
        args = conn.execute.call_args[0]
        assert "s2s_inbox_users" in args[0]
        assert "DELETE" in args[0]
        assert args[1] == "alice"


@pytest.mark.asyncio
async def test_delete_user_not_exists(fake_pool):
    store = await storage.storage()
    await store.delete("bob")

    async with fake_pool.acquire() as conn:
        args = conn.execute.call_args[0]
        assert "s2s_inbox_users" in args[0]
        assert "DELETE" in args[0]
        assert args[1] == "bob"


@pytest.mark.asyncio
async def test_user_exists_found(fake_pool):
    async with fake_pool.acquire() as conn:
        conn.fetchrow.return_value = {"c": 1}
        store = await storage.storage()
        assert await store.exists("alice@example.com")


@pytest.mark.asyncio
async def test_user_exists_not_found(fake_pool):
    async with fake_pool.acquire() as conn:
        conn.fetchrow.return_value = {"c": 0}
        store = await storage.storage()
        assert not await store.exists("alice@example.com")


@pytest.mark.asyncio
async def test_ensure_schema_executes_create(fake_pool):
    store = await storage.storage()
    await store.ensure_schema()

    async with fake_pool.acquire() as conn:
        conn.execute.assert_awaited()


@pytest.mark.asyncio
async def test_storage_not_initialized():
    storage.overwrite(None)

    with pytest.raises(RuntimeError):
        await storage.storage()

