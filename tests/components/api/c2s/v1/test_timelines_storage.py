# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, Mock
from profed.components.api.c2s.v1.timelines import storage as module


ACTOR_URL = "https://remote.example/actors/bob"
STATUS = {"id": "42", "content": "<p>hi</p>"}


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
    module._instance = module._storage(pool)
    yield conn
    module._instance = backup


@pytest.mark.asyncio
async def test_get_by_id_returns_tuple_when_found(fake_pool):
    fake_pool.fetchrow.return_value = {"actor_url": ACTOR_URL, "status": STATUS}

    result = await (await module.storage()).get_by_id("alice", "42")

    assert result == (ACTOR_URL, STATUS)
    sql = fake_pool.fetchrow.call_args[0][0]
    assert "c2s_home_timeline" in sql
    assert "numeric" in sql.lower()


@pytest.mark.asyncio
async def test_get_by_id_returns_none_when_not_found(fake_pool):
    fake_pool.fetchrow.return_value = None

    result = await (await module.storage()).get_by_id("alice", "42")

    assert result is None

