# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, Mock
from profed.components.api.s2s.webfinger import storage as webfinger_users


@pytest.fixture
def fake_conn():
    conn = Mock()
    conn.execute = AsyncMock()
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

    webfinger_users.reinit(pool)
    return pool


@pytest.mark.asyncio
async def test_add_user_success(fake_pool):
    store = await webfinger_users.storage()
    await store.add("alice")

    async with fake_pool.acquire() as conn:
        args = conn.execute.call_args[0]
        assert "s2s_webfinger_users" in args[0]
        assert "INSERT" in args[0]
        assert args[1] == "alice"


@pytest.mark.asyncio
async def test_add_user_already_exists(fake_pool):
    store = await webfinger_users.storage()
    await store.add("alice")

    async with fake_pool.acquire() as conn:
        args = conn.execute.call_args[0]
        assert "s2s_webfinger_users" in args[0]
        assert "INSERT" in args[0]
        assert args[1] == "alice"


@pytest.mark.asyncio
async def test_delete_user_success(fake_pool):
    store = await webfinger_users.storage()
    await store.delete("alice")

    async with fake_pool.acquire() as conn:
        args = conn.execute.call_args[0]
        assert "s2s_webfinger_users" in args[0]
        assert "DELETE" in args[0]
        assert args[1] == "alice"


@pytest.mark.asyncio
async def test_delete_user_not_exists(fake_pool):
    store = await webfinger_users.storage()
    await store.delete("bob")

    async with fake_pool.acquire() as conn:
        args = conn.execute.call_args[0]
        assert "s2s_webfinger_users" in args[0]
        assert "DELETE" in args[0]
        assert args[1] == "bob"


@pytest.mark.asyncio
async def test_user_exists_found(fake_pool):
    async with fake_pool.acquire() as conn:
        conn.fetchrow.return_value = {"c": 1}
        store = await webfinger_users.storage()
        assert await store.exists("alice@example.com")


@pytest.mark.asyncio
async def test_user_exists_not_found(fake_pool):
    async with fake_pool.acquire() as conn:
        conn.fetchrow.return_value = {"c": 0}
        store = await webfinger_users.storage()
        assert not await store.exists("alice@example.com")


@pytest.mark.asyncio
async def test_ensure_schema_executes_create(fake_pool):
    store = await webfinger_users.storage()
    await store.ensure_schema()

    async with fake_pool.acquire() as conn:
        conn.execute.assert_awaited()


@pytest.mark.asyncio
async def test_storage_not_initialized():
    webfinger_users.overwrite(None)

    with pytest.raises(RuntimeError):
        await webfinger_users.storage()

