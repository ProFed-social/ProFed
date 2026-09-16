# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from profed.components.reaction_collections import storage as module


NOW = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def fake_conn():
    conn = MagicMock()
    conn.execute = AsyncMock()
    conn.fetch = AsyncMock(return_value=[{"object_url": "https://r/1",
                                          "attempt": 0,
                                          "collection_url": "https://r/1/emojiReactions"}])
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
async def test_the_schema_holds_the_collections_and_the_state(fake_pool, fake_conn):
    await (await _storage(fake_pool)).ensure_schema()

    statements = [call.args[0] for call in fake_conn.execute.await_args_list]
    assert any("reaction_collections.collection" in s and "PRIMARY KEY (object_url)" in s for s in statements)
    assert any("reaction_collections.inspection" in s and "next_due_at" in s and "attempt" in s
               for s in statements)


@pytest.mark.asyncio
async def test_a_collection_is_remembered_for_its_object(fake_pool, fake_conn):
    await (await _storage(fake_pool)).remember("https://r/1", "https://r/1/emojiReactions")

    sql, *args = fake_conn.execute.await_args.args
    assert "ON CONFLICT (object_url) DO UPDATE" in sql
    assert args == ["https://r/1", "https://r/1/emojiReactions"]


@pytest.mark.asyncio
async def test_only_objects_with_a_known_collection_are_due(fake_pool, fake_conn):
    due = await (await _storage(fake_pool)).due(["https://r/1"], NOW, timedelta(minutes=5))

    sql, *args = fake_conn.fetch.await_args.args
    assert "reaction_collections.collection AS c LEFT JOIN" in sql
    assert "c.object_url = ANY($1::text[])" in sql
    assert args == [["https://r/1"], NOW, timedelta(minutes=5)]
    assert due[0]["collection_url"] == "https://r/1/emojiReactions"


@pytest.mark.asyncio
async def test_an_object_nobody_looked_at_yet_is_due(fake_pool, fake_conn):
    await (await _storage(fake_pool)).due(["https://r/1"], NOW, timedelta(minutes=5))

    assert "i.object_url IS NULL OR" in fake_conn.fetch.await_args.args[0]


@pytest.mark.asyncio
async def test_work_that_is_still_running_is_not_due(fake_pool, fake_conn):
    await (await _storage(fake_pool)).due(["https://r/1"], NOW, timedelta(minutes=5))

    sql = fake_conn.fetch.await_args.args[0]
    assert "i.state = 'attempting' AND i.checked_at < $2::timestamptz - $3::interval" in sql


@pytest.mark.asyncio
async def test_an_object_is_due_again_at_its_next_turn(fake_pool, fake_conn):
    await (await _storage(fake_pool)).due(["https://r/1"], NOW, timedelta(minutes=5))

    sql = fake_conn.fetch.await_args.args[0]
    assert "i.state <> 'attempting' AND i.next_due_at <= $2::timestamptz" in sql


@pytest.mark.asyncio
async def test_the_number_of_attempts_comes_along(fake_pool, fake_conn):
    due = await (await _storage(fake_pool)).due(["https://r/1"], NOW, timedelta(minutes=5))

    assert "COALESCE(i.attempt, 0) AS attempt" in fake_conn.fetch.await_args.args[0]
    assert due[0]["attempt"] == 0



@pytest.mark.asyncio
async def test_the_parameters_of_due_carry_their_types(fake_pool, fake_conn):
    await (await _storage(fake_pool)).due(["https://r/1"], NOW, timedelta(minutes=5))

    sql = fake_conn.fetch.await_args.args[0]
    assert "$2 - $3" not in sql
    assert "$1::text[]" in sql


@pytest.mark.asyncio
async def test_the_next_turn_falls_back_to_the_moment_it_was_checked(fake_pool, fake_conn):
    await (await _storage(fake_pool)).record("https://r/1", "attempting", NOW, None, 0)

    sql = fake_conn.execute.await_args.args[0]
    assert "COALESCE($4::timestamptz, $3::timestamptz)" in sql


@pytest.mark.asyncio
async def test_a_state_is_recorded_with_its_next_turn(fake_pool, fake_conn):
    await (await _storage(fake_pool)).record("https://r/1", "failed", NOW, NOW + timedelta(minutes=1), 3)

    sql, *args = fake_conn.execute.await_args.args
    assert "ON CONFLICT (object_url) DO UPDATE" in sql
    assert args == ["https://r/1", "failed", NOW, NOW + timedelta(minutes=1), 3]


@pytest.mark.asyncio
async def test_an_older_report_does_not_overwrite_a_newer_one(fake_pool, fake_conn):
    await (await _storage(fake_pool)).record("https://r/1", "failed", NOW, None, 3)

    sql = fake_conn.execute.await_args.args[0]
    assert "reaction_collections.inspection.checked_at <= EXCLUDED.checked_at" in sql

