# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timezone
import pytest
from unittest.mock import AsyncMock, Mock
from profed.components.polish_activities.storage import _Storage


NOW = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def fake_conn():
    conn = Mock()
    conn.execute = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    return conn


@pytest.fixture
def store(fake_conn):
    class _Ctx:
        def __init__(self, conn):
            self.conn = conn

        async def __aenter__(self):
            return self.conn

        async def __aexit__(self, *_):
            pass

    pool = Mock()
    pool.acquire = Mock(return_value=_Ctx(fake_conn))
    return _Storage(pool)


@pytest.mark.asyncio
async def test_ensure_schema_creates_all_three_tables(store, fake_conn):
    await store.ensure_schema()

    statements = " ".join(call.args[0] for call in fake_conn.execute.await_args_list)
    assert "polish_activities.actors" in statements
    assert "polish_activities.unfinished_objects" in statements
    assert "polish_activities.unresolved_actors" in statements


@pytest.mark.asyncio
async def test_the_waiting_list_is_cleared_with_its_object(store, fake_conn):
    await store.ensure_schema()

    statements = " ".join(call.args[0] for call in fake_conn.execute.await_args_list)
    assert "ON DELETE CASCADE" in statements


@pytest.mark.asyncio
async def test_an_actor_is_remembered_by_acct(store, fake_conn):
    await store.remember_actor("ghost@r.io", "https://r.io/ghost")

    sql, *args = fake_conn.execute.await_args.args
    assert "INSERT INTO polish_activities.actors" in sql
    assert "ON CONFLICT (acct) DO UPDATE" in sql
    assert args == ["ghost@r.io", "https://r.io/ghost"]


@pytest.mark.asyncio
async def test_an_actor_is_forgotten_by_acct(store, fake_conn):
    await store.forget_actor("ghost@r.io")

    sql, *args = fake_conn.execute.await_args.args
    assert "DELETE FROM polish_activities.actors" in sql
    assert args == ["ghost@r.io"]


@pytest.mark.asyncio
async def test_the_url_of_a_known_acct_is_returned(store, fake_conn):
    fake_conn.fetchrow.return_value = {"actor_url": "https://r.io/ghost"}

    assert await store.url_for("ghost@r.io") == "https://r.io/ghost"


@pytest.mark.asyncio
async def test_an_unknown_acct_has_no_url(store, fake_conn):
    assert await store.url_for("ghost@r.io") is None


@pytest.mark.asyncio
async def test_holding_an_object_writes_it_and_its_pending_accts(store, fake_conn):
    await store.hold("https://a/1", "Create", "act1", "{}", NOW, ["ghost@r.io"])

    statements = [call.args[0] for call in fake_conn.execute.await_args_list]
    assert "INSERT INTO polish_activities.unfinished_objects" in statements[0]
    assert "DELETE FROM polish_activities.unresolved_actors" in statements[1]
    assert "INSERT INTO polish_activities.unresolved_actors" in statements[2]


@pytest.mark.asyncio
async def test_holding_an_object_again_replaces_its_payload(store, fake_conn):
    await store.hold("https://a/1", "Update", "act1", "{}", NOW, ["ghost@r.io"])

    assert "ON CONFLICT (url) DO UPDATE" in fake_conn.execute.await_args_list[0].args[0]


@pytest.mark.asyncio
async def test_holding_an_object_drops_accts_it_no_longer_waits_for(store, fake_conn):
    await store.hold("https://a/1", "Update", "act1", "{}", NOW, ["ghost@r.io"])

    sql, *args = fake_conn.execute.await_args_list[1].args
    assert "acct <> ALL ($2::text[])" in sql
    assert args == ["https://a/1", ["ghost@r.io"]]


@pytest.mark.asyncio
async def test_releasing_an_object_removes_it(store, fake_conn):
    await store.release("https://a/1")

    sql, *args = fake_conn.execute.await_args.args
    assert "DELETE FROM polish_activities.unfinished_objects" in sql
    assert args == ["https://a/1"]


@pytest.mark.asyncio
async def test_the_objects_waiting_for_an_acct_are_joined(store, fake_conn):
    fake_conn.fetch.return_value = [{"url": "https://a/1"}]

    result = await store.waiting_for("ghost@r.io")

    sql, *args = fake_conn.fetch.await_args.args
    assert "JOIN polish_activities.unresolved_actors" in sql
    assert args == ["ghost@r.io"]
    assert result[0]["url"] == "https://a/1"


@pytest.mark.asyncio
async def test_old_objects_are_dropped_by_their_age(store, fake_conn):
    await store.drop_older_than(NOW)

    sql, *args = fake_conn.execute.await_args.args
    assert "emitted_at < $1" in sql
    assert args == [NOW]

