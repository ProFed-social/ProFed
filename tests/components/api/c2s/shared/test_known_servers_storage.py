# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
import profed.components.api.c2s.shared.known_servers.storage as module


AT = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def fake_pool():
    conn = Mock()
    conn.execute = AsyncMock()
    conn.fetchrow = AsyncMock(return_value=None)

    class _Ctx:
        async def __aenter__(self):
            return conn

        async def __aexit__(self, *_):
            pass

    pool = Mock()
    pool.acquire = Mock(return_value=_Ctx())

    backup = module._instance
    module._instance = module._Storage(pool)
    yield conn
    module._instance = backup


@pytest.mark.asyncio
async def test_an_unknown_host_has_no_answer(fake_pool):
    assert await (await module.storage()).support_of("a.test") is None


@pytest.mark.asyncio
async def test_a_known_host_answers_with_its_support(fake_pool):
    fake_pool.fetchrow.return_value = {"supported": True}

    assert await (await module.storage()).support_of("a.test") is True


@pytest.mark.asyncio
async def test_support_follows_an_observation_or_the_feature_list(fake_pool):
    await (await module.storage()).support_of("a.test")

    sql = fake_pool.fetchrow.await_args.args[0]
    assert "reacted_at IS NOT NULL" in sql
    assert "'pleroma_emoji_reactions'" in sql


@pytest.mark.asyncio
async def test_support_counts_the_neutral_feature_name_too(fake_pool):
    await (await module.storage()).support_of("a.test")

    sql = fake_pool.fetchrow.await_args.args[0]
    assert "features ?|" in sql
    assert "'emoji_reactions'" in sql


@pytest.mark.asyncio
async def test_an_observation_never_moves_backwards(fake_pool):
    await (await module.storage()).record_observation("a.test", AT)

    sql = fake_pool.execute.await_args.args[0]
    assert "GREATEST(api.known_servers.reacted_at, EXCLUDED.reacted_at)" in sql
    assert fake_pool.execute.await_args.args[1:] == ("a.test", AT)


@pytest.mark.asyncio
async def test_an_update_replaces_software_features_and_time(fake_pool):
    await (await module.storage()).record_update("a.test", "pleroma", ["pleroma_emoji_reactions"], AT)

    assert fake_pool.execute.await_args.args[1:] == ("a.test",
                                                     "pleroma",
                                                     json.dumps(["pleroma_emoji_reactions"]),
                                                     AT)


@pytest.mark.asyncio
async def test_an_update_leaves_an_observation_alone(fake_pool):
    await (await module.storage()).record_update("a.test", "pleroma", [], AT)

    assert "reacted_at" not in fake_pool.execute.await_args.args[0]

