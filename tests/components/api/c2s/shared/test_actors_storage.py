# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import pytest
from unittest.mock import AsyncMock, Mock
from profed.components.api.c2s.shared.actors import storage as actors
 
 
@pytest.fixture
def fake_pool():
    conn = Mock()
    conn.execute  = AsyncMock()
    conn.fetchrow = AsyncMock()
 
    class _Ctx:
        async def __aenter__(self): return conn
        async def __aexit__(self, *_): pass
 
    pool = Mock()
    pool.acquire = Mock(return_value=_Ctx())
 
    backup = actors._instance
    actors._instance = actors._storage(pool)
    yield pool
    actors._instance = backup
 
 
@pytest.mark.asyncio
async def test_add_inserts_row(fake_pool):
    store = await actors.storage()
    await store.add("alice", {"name": "Alice"})
    async with fake_pool.acquire() as conn:
        conn.execute.assert_called_once()
        sql = conn.execute.call_args[0][0]
        assert "c2s_actor" in sql
 
 
@pytest.mark.asyncio
async def test_update_updates_row(fake_pool):
    store = await actors.storage()
    await store.update("alice", {"name": "Alice Updated"})
    async with fake_pool.acquire() as conn:
        conn.execute.assert_called_once()
 
 
@pytest.mark.asyncio
async def test_delete_deletes_row(fake_pool):
    store = await actors.storage()
    await store.delete("alice")
    async with fake_pool.acquire() as conn:
        conn.execute.assert_called_once()
 
 
@pytest.mark.asyncio
async def test_fetch_returns_payload(fake_pool):
    store = await actors.storage()
    async with fake_pool.acquire() as conn:
        conn.fetchrow.return_value = {"payload": {"name": "Alice"}}
        result = await store.fetch("alice")
    assert result == {"name": "Alice"}
 
 
@pytest.mark.asyncio
async def test_fetch_returns_none_when_not_found(fake_pool):
    store = await actors.storage()
    async with fake_pool.acquire() as conn:
        conn.fetchrow.return_value = None
        result = await store.fetch("alice")
    assert result is None

