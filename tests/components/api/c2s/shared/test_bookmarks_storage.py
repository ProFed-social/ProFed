# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, MagicMock
from profed.components.api.c2s.shared.bookmarks import storage as module


ALICE = "https://example.com/actors/alice"

NOTE = "https://remote.example/notes/7"


@pytest.fixture
def fake_conn():
    conn = MagicMock()
    conn.execute = AsyncMock()
    conn.fetch = AsyncMock(return_value=[{"object_url": NOTE, "marked_at": 500}])
    return conn


@pytest.fixture
def fake_pool(fake_conn, monkeypatch):
    pool = MagicMock()
    pool.acquire = MagicMock(return_value=MagicMock(__aenter__=AsyncMock(return_value=fake_conn),
                                                    __aexit__=AsyncMock(return_value=False)))
    monkeypatch.setattr(module, "init_pool", AsyncMock(return_value=pool))
    module._instance = None
    yield pool
    module._instance = None


async def _storage(fake_pool):
    await module.init({})
    store = await module.storage()
    store.rebuild_finished()
    return store


@pytest.mark.asyncio
async def test_the_schema_holds_one_row_per_actor_and_object(fake_pool, fake_conn):
    await (await _storage(fake_pool)).ensure_schema()

    statements = [call.args[0] for call in fake_conn.execute.await_args_list]
    assert any("api.bookmarks" in s and "PRIMARY KEY (actor_url, object_url)" in s for s in statements)
    assert any("bookmarks_of_an_actor" in s and "(actor_url, marked_at DESC)" in s for s in statements)


@pytest.mark.asyncio
async def test_adding_the_same_bookmark_twice_keeps_the_first_moment(fake_pool, fake_conn):
    await (await _storage(fake_pool)).add(ALICE, NOTE, 500)

    sql, *args = fake_conn.execute.await_args.args
    assert "ON CONFLICT (actor_url, object_url) DO NOTHING" in sql
    assert args == [ALICE, NOTE, 500]


@pytest.mark.asyncio
async def test_removing_touches_only_this_actors_bookmark(fake_pool, fake_conn):
    await (await _storage(fake_pool)).remove(ALICE, NOTE)

    sql, *args = fake_conn.execute.await_args.args
    assert "actor_url = $1 AND" in sql
    assert "object_url = $2" in sql
    assert args == [ALICE, NOTE]


@pytest.mark.asyncio
async def test_a_page_is_newest_first_and_belongs_to_one_actor(fake_pool, fake_conn):
    page = await (await _storage(fake_pool)).page(ALICE, 20, None, None)

    sql, *args = fake_conn.fetch.await_args.args
    assert "actor_url = $1 AND" in sql
    assert "ORDER BY\n                marked_at DESC" in sql
    assert args == [ALICE, 20, None, None]
    assert page[0]["object_url"] == NOTE


@pytest.mark.asyncio
async def test_a_page_can_start_after_a_cursor(fake_pool, fake_conn):
    await (await _storage(fake_pool)).page(ALICE, 20, "500", "100")

    sql = fake_conn.fetch.await_args.args[0]
    assert "marked_at < $3::bigint" in sql
    assert "marked_at > $4::bigint" in sql


@pytest.mark.asyncio
async def test_what_is_marked_comes_back_as_a_set(fake_pool, fake_conn):
    marked = await (await _storage(fake_pool)).marked([NOTE, "https://r/9"], ALICE)

    sql, *args = fake_conn.fetch.await_args.args
    assert "object_url = ANY($2::text[])" in sql
    assert args == [ALICE, [NOTE, "https://r/9"]]
    assert marked == {NOTE}


@pytest.mark.asyncio
async def test_nobody_asks_the_database_for_an_anonymous_viewer(fake_pool, fake_conn):
    marked = await (await _storage(fake_pool)).marked([NOTE], None)

    assert marked == set()
    assert fake_conn.fetch.await_count == 0

