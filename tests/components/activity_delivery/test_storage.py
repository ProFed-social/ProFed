# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import pytest
from unittest.mock import AsyncMock, Mock
from profed.components.activity_delivery import storage as storage_module
from profed.components.activity_delivery.storage import _Storage
 
 
@pytest.fixture
def fake_conn():
    conn = Mock()
    conn.execute = AsyncMock()
    conn.fetch   = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    return conn
 
 
@pytest.fixture
def store(fake_conn):
    class _Ctx:
        def __init__(self, conn): self.conn = conn
        async def __aenter__(self): return self.conn
        async def __aexit__(self, *_): pass
    pool = Mock()
    pool.acquire = Mock(return_value=_Ctx(fake_conn))
    return _Storage(pool)
 
 
@pytest.mark.asyncio
async def test_add_follower(store, fake_conn):
    await store.add_follower("alice@example.com", "bob@remote.example")
    fake_conn.execute.assert_awaited_once()
    call_args = fake_conn.execute.call_args[0]
    assert "INSERT" in call_args[0]
    assert call_args[1] == "alice@example.com"
    assert call_args[2] == "bob@remote.example"
 
 
@pytest.mark.asyncio
async def test_remove_follower(store, fake_conn):
    await store.remove_follower("alice@example.com", "bob@remote.example")
    fake_conn.execute.assert_awaited_once()
    call_args = fake_conn.execute.call_args[0]
    assert "DELETE" in call_args[0]
    assert call_args[1] == "alice@example.com"
    assert call_args[2] == "bob@remote.example"
 
 
@pytest.mark.asyncio
async def test_get_followers_empty(store, fake_conn):
    fake_conn.fetch.return_value = []
    result = await store.get_followers("alice@example.com")
    assert result == set()
 
 
@pytest.mark.asyncio
async def test_get_followers_returns_set(store, fake_conn):
    fake_conn.fetch.return_value = [{"follower": "bob@remote.example"},
                                    {"follower": "carol@other.example"}]
    result = await store.get_followers("alice@example.com")
    assert result == {"bob@remote.example", "carol@other.example"}
 
 
@pytest.mark.asyncio
async def test_upsert_delivery(store, fake_conn):
    payload = {"activity_id": "https://example.com/act/1",
               "recipient":   "bob@remote.example",
               "success":     True,
               "attempt":     1,
               "status_code": 202,
               "retry_after": None,
               "first_attempt_at": 1000.0}
    await store.upsert_delivery(payload)
    fake_conn.execute.assert_awaited_once()
    call_args = fake_conn.execute.call_args[0]
    assert "INSERT" in call_args[0]
    assert call_args[1] == "https://example.com/act/1"
    assert call_args[3] is True
 
 
@pytest.mark.asyncio
async def test_get_delivery_status_not_found(store, fake_conn):
    fake_conn.fetchrow.return_value = None
    result = await store.get_delivery_status("https://example.com/act/1",
                                              "bob@remote.example")
    assert result is None
 
 
@pytest.mark.asyncio
async def test_get_delivery_status_found(store, fake_conn):
    fake_conn.fetchrow.return_value = {"activity_id": "https://example.com/act/1",
                                        "recipient":   "bob@remote.example",
                                        "success":     True,
                                        "attempt":     1,
                                        "status_code": 202,
                                        "retry_after": None,
                                        "first_attempt_at": 1000.0}
    result = await store.get_delivery_status("https://example.com/act/1",
                                              "bob@remote.example")
    assert result["success"] is True
    assert result["attempt"] == 1

