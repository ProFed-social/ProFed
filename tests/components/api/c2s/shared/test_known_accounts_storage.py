# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
import profed.components.api.c2s.shared.known_accounts.storage as module 
 
NOW = datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)
ACTOR_DATA = {"type": "Person", "name": "Alice"}
 
 
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
 
    backup = module._instance
    module._instance = module._Storage(pool)
    yield pool
    module._instance = backup
 
 
@pytest.mark.asyncio
async def test_upsert_calls_execute(fake_pool):
    store = await module.storage()
    await store.upsert(1234, "alice@example.com",
                       "https://example.com/actors/alice",
                       ACTOR_DATA, NOW)

    async with fake_pool.acquire() as conn:
        conn.execute.assert_called_once()
        sql = conn.execute.call_args[0][0]

        assert "known_accounts" in sql
 
 
@pytest.mark.asyncio
async def test_get_by_id_returns_row(fake_pool):
    store = await module.storage()
    async with fake_pool.acquire() as conn:
        conn.fetchrow.return_value = {"account_id": 1234,
                                      "acct": "alice@example.com",
                                      "actor_url": "https://example.com/actors/alice",
                                      "actor_data": ACTOR_DATA,
                                      "last_webfinger_at": NOW}
        result = await store.get_by_id(1234)

    assert result is not None
    assert result["acct"] == "alice@example.com"
 
 
@pytest.mark.asyncio
async def test_get_by_id_returns_none_when_missing(fake_pool):
    store = await module.storage()
    async with fake_pool.acquire() as conn:
        conn.fetchrow.return_value = None
        result = await store.get_by_id(9999)

    assert result is None
 
 
@pytest.mark.asyncio
async def test_get_by_acct_returns_row(fake_pool):
    store = await module.storage()
    async with fake_pool.acquire() as conn:
        conn.fetchrow.return_value = {"account_id": 1234,
                                      "acct": "alice@example.com",
                                      "actor_url": "https://example.com/actors/alice",
                                      "actor_data": ACTOR_DATA,
                                      "last_webfinger_at": NOW}
        result = await store.get_by_acct("alice@example.com")

    assert result is not None
    assert result["account_id"] == 1234
 
 
@pytest.mark.asyncio
async def test_get_by_actor_url_returns_row(fake_pool):
    store = await module.storage()
    async with fake_pool.acquire() as conn:
        conn.fetchrow.return_value = {"account_id": 1234,
                                      "acct": "alice@example.com",
                                      "actor_url": "https://example.com/actors/alice",
                                      "actor_data": ACTOR_DATA,
                                      "last_webfinger_at": NOW}
        result = await store.get_by_actor_url("https://example.com/actors/alice")

    assert result is not None
    assert result["acct"] == "alice@example.com"
 
 
@pytest.mark.asyncio
async def test_storage_raises_when_not_initialized():
    backup = module._instance
    module._instance = None
    with pytest.raises(RuntimeError):
        await module.storage()
    module._instance = backup

