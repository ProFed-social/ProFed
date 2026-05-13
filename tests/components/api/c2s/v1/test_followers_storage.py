# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, Mock
from profed.components.api.c2s.v1.accounts.followers import storage as module


@pytest.fixture
def fake_pool():
    conn = Mock()
    conn.execute  = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetch    = AsyncMock(return_value=[])
    class _Ctx:
        async def __aenter__(self): return conn
        async def __aexit__(self, *_): pass
    pool = Mock()
    pool.acquire = Mock(return_value=_Ctx())
    backup           = module._instance
    module._instance = module._storage(pool)
    yield conn
    module._instance = backup


@pytest.mark.asyncio
async def test_add_follower_inserts_row(fake_pool):
    await (await module.storage()).add_follower("christof@example.com",
                                                "alice@other.example")

    sql = fake_pool.execute.call_args[0][0]
    assert "c2s_followers" in sql
    assert "INSERT"        in sql


@pytest.mark.asyncio
async def test_remove_follower_deletes_row(fake_pool):
    await (await module.storage()).remove_follower("christof@example.com",
                                                   "alice@other.example")

    sql = fake_pool.execute.call_args[0][0]
    assert "c2s_followers" in sql
    assert "DELETE"        in sql


@pytest.mark.asyncio
async def test_get_followers_returns_list(fake_pool):
    fake_pool.fetch.return_value = [{"follower": "alice@other.example"},
                                    {"follower": "bob@remote.example"}]

    result = await (await module.storage()).get_followers("christof@example.com")

    assert set(result) == {"alice@other.example", "bob@remote.example"}


@pytest.mark.asyncio
async def test_get_followers_returns_empty_list_when_none(fake_pool):
    fake_pool.fetch.return_value = []

    result = await (await module.storage()).get_followers("nobody@example.com")

    assert result == []

