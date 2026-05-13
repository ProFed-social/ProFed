# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, Mock
from profed.components.api.c2s.v1.timelines import storage as module


ACTIVITY = {"type": "Create", "actor": "https://remote.example/actors/bob"}
UUID     = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


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
    fake_pool.fetchrow.return_value = {"id": UUID, "activity": ACTIVITY}

    result = await (await module.storage()).get_by_id(UUID)

    assert result == (UUID, ACTIVITY)
    sql = fake_pool.fetchrow.call_args[0][0]
    assert "c2s_home_timeline" in sql
    assert "uuid" in sql.lower()


@pytest.mark.asyncio
async def test_get_by_id_returns_none_when_not_found(fake_pool):
    fake_pool.fetchrow.return_value = None

    result = await (await module.storage()).get_by_id(UUID)

    assert result is None

