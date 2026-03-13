# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, Mock
from profed.components.api import storage

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

    storage._instance = storage._webfinger_storage(pool, "test_schema")
    return pool


@pytest.mark.asyncio
async def test_add_user_success(fake_pool):
    store = await storage.webfinger_storage()
    await store.add("alice@example.com", "https://example.com/alice")

    async with fake_pool.acquire() as conn:
        conn.execute.assert_awaited_with(
                               f"""
                               INSERT INTO {store._schema_name}.webfinger_users (acct, actor_url)
                               VALUES ($1, $2)
                               ON CONFLICT (acct) DO NOTHING
                               """,
                               "alice@example.com",
                               "https://example.com/alice")


@pytest.mark.asyncio
async def test_add_user_already_exists(fake_pool):
    store = await storage.webfinger_storage()
    await store.add("alice@example.com", "https://example.com/alice")

    # same as successful operation, conflict is handled in SQL
    async with fake_pool.acquire() as conn:
        conn.execute.assert_awaited_with(
                               f"""
                               INSERT INTO {store._schema_name}.webfinger_users (acct, actor_url)
                               VALUES ($1, $2)
                               ON CONFLICT (acct) DO NOTHING
                               """,
                               "alice@example.com",
                               "https://example.com/alice")


@pytest.mark.asyncio
async def test_update_user_success(fake_pool):
    store = await storage.webfinger_storage()
    await store.update("alice@example.com", "https://example.com/alice_new")

    async with fake_pool.acquire() as conn:
        conn.execute.assert_awaited_with(
                               f"""
                               UPDATE {store._schema_name}.webfinger_users
                               SET actor_url = $2
                               WHERE acct = $1
                               """,
                               "alice@example.com",
                               "https://example.com/alice_new")


@pytest.mark.asyncio
async def test_update_user_not_exists(fake_pool):
    store = await storage.webfinger_storage()
    await store.update("bob@example.com", "https://example.com/bob")

    # same as successful operation, conflict is handled in SQL
    async with fake_pool.acquire() as conn:
        conn.execute.assert_awaited_with(
                               f"""
                               UPDATE {store._schema_name}.webfinger_users
                               SET actor_url = $2
                               WHERE acct = $1
                               """,
                               "bob@example.com",
                               "https://example.com/bob")


@pytest.mark.asyncio
async def test_delete_user_success(fake_pool):
    store = await storage.webfinger_storage()
    await store.delete("alice@example.com", None)

    async with fake_pool.acquire() as conn:
        conn.execute.assert_awaited_with(
                               f"""
                               DELETE FROM {store._schema_name}.webfinger_users
                               WHERE acct = $1
                               """,
                               "alice@example.com")


@pytest.mark.asyncio
async def test_delete_user_not_exists(fake_pool):
    store = await storage.webfinger_storage()
    await store.delete("bob@example.com", None)

    # same as successful operation, conflict is handled in SQL
    async with fake_pool.acquire() as conn:
        conn.execute.assert_awaited_with(
                               f"""
                               DELETE FROM {store._schema_name}.webfinger_users
                               WHERE acct = $1
                               """,
                               "bob@example.com")


@pytest.mark.asyncio
async def test_fetch_actor_url_found(fake_pool):
    async with fake_pool.acquire() as conn:
        conn.fetchrow.return_value = {"actor_url": "https://example.com/alice"}

        store = await storage.webfinger_storage()
        result = await store.fetch_actor_url("alice@example.com")

        assert result == "https://example.com/alice"


@pytest.mark.asyncio
async def test_fetch_actor_url_not_found(fake_pool):
    async with fake_pool.acquire() as conn:
        conn.fetchrow.return_value = None

        store = await storage.webfinger_storage()
        result = await store.fetch_actor_url("unknown@example.com")

        assert result is None


@pytest.mark.asyncio
async def test_ensure_table_executes_create(fake_pool):
    store = await storage.webfinger_storage()
    await store.ensure_table()

    async with fake_pool.acquire() as conn:
        conn.execute.assert_awaited()


@pytest.mark.asyncio
async def test_webfinger_storage_not_initialized():
    storage._instance = None

    with pytest.raises(RuntimeError):
        await storage.webfinger_storage()

