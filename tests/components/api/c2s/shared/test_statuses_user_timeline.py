# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import re

import pytest
from unittest.mock import AsyncMock, Mock
from profed.components.api.c2s.shared.statuses import user_timeline


@pytest.fixture
def fake_conn():
    conn = Mock()
    conn.execute = AsyncMock()
    conn.fetch = AsyncMock()

    return conn


@pytest.fixture
def fake_pool(fake_conn):
    class AsyncContextManagerMock:
        def __init__(self, conn):
            self.conn = conn
        async def __aenter__(self):
            return self.conn
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
    pool = Mock()
    pool.acquire = Mock(return_value=AsyncContextManagerMock(fake_conn))
    backup = user_timeline._instance
    user_timeline._instance = user_timeline._storage(pool)

    yield pool

    user_timeline._instance = backup


@pytest.mark.asyncio
async def test_ensure_schema_creates_the_membership_table(fake_pool, fake_conn):
    await (await user_timeline.storage()).ensure_schema()

    assert fake_conn.execute.await_count == 1
    assert "CREATE TABLE" in fake_conn.execute.await_args_list[0].args[0]
    assert "PRIMARY KEY (username, object_url)" in fake_conn.execute.await_args_list[0].args[0]
    assert "mastodon_id" not in fake_conn.execute.await_args_list[0].args[0]


@pytest.mark.asyncio
async def test_add_inserts_the_membership(fake_pool, fake_conn):
    await (await user_timeline.storage()).add("alice", "https://r/1")

    sql, *args = fake_conn.execute.await_args.args
    assert "INSERT INTO api.user_timeline\n                                          (username, object_url)" in sql
    assert "ON CONFLICT (username, object_url) DO NOTHING" in sql
    assert args == ["alice", "https://r/1"]


@pytest.mark.asyncio
async def test_remove_deletes_one_users_entry(fake_pool, fake_conn):
    await (await user_timeline.storage()).remove("alice", "https://r/1")

    sql, *args = fake_conn.execute.await_args.args
    assert "DELETE FROM api.user_timeline" in sql
    assert "username = $1 AND object_url = $2" in sql
    assert args == ["alice", "https://r/1"]


@pytest.mark.asyncio
async def test_remove_object_deletes_the_entry_for_every_user(fake_pool, fake_conn):
    await (await user_timeline.storage()).remove_object("https://r/1")

    sql, *args = fake_conn.execute.await_args.args
    assert "DELETE FROM api.user_timeline" in sql
    assert "WHERE object_url = $1" in sql
    assert args == ["https://r/1"]


@pytest.mark.asyncio
async def test_fetch_joins_resolves_filters_and_paginates(fake_pool, fake_conn):
    fake_conn.fetch.return_value = [{"mastodon_id": 102, "kind": "announce", "content": {"id": "100"}},
                                    {"mastodon_id": 100, "kind": "content", "content": {"id": "100"}}]

    result = await (await user_timeline.storage()).fetch("alice", limit=5, max_id="999")

    sql, *args = fake_conn.fetch.await_args.args
    assert "api.user_timeline AS ut ON ut.object_url = o.url" in sql
    assert "api.resolve_content(o.url)" in sql
    assert "r.content IS NOT NULL" in sql
    assert "ut.username = $1" in sql
    assert re.search(r"ORDER BY\s+o\.mastodon_id DESC", sql)
    assert args == ["alice", 5, "999", None, None]
    assert [row["mastodon_id"] for row in result] == [102, 100]


@pytest.mark.asyncio
async def test_thread_roots_streams_rows_with_thread_root_and_booster(fake_pool):
    st = await user_timeline.storage()
    captured = {}

    async def fake_stream(sql, *args):
        captured["sql"] = sql
        captured["args"] = args
        for row in [{"mastodon_id": 7, "root": "s1", "booster": None}]:
            yield row

    st.stream = fake_stream
    rows = [row async for row in st.thread_roots("me", max_depth=10)]

    assert "api.thread_root(api.content_url(o.url), $2) AS root" in captured["sql"]
    assert "JOIN api.user_timeline ut ON ut.object_url = o.url" in captured["sql"]
    assert "WHERE ut.username = $1" in captured["sql"]
    assert "ORDER BY o.mastodon_id DESC" in captured["sql"]
    assert captured["args"] == ("me", 10)
    assert rows == [{"mastodon_id": 7, "root": "s1", "booster": None}]


@pytest.mark.asyncio
async def test_fetch_also_weighs_the_post_a_boost_points_at(fake_pool, fake_conn):
    fake_conn.fetch.return_value = []

    await (await user_timeline.storage()).fetch("alice", viewer="https://example.com/actors/alice")

    sql, *args = fake_conn.fetch.await_args.args
    assert "target AS t ON t.url = COALESCE(o.target_url, o.url)" in sql
    assert "t.visibility = 'public'" in sql
    assert "ta.object_url IS NOT NULL" in sql
    assert "t.visibility = 'followers' AND tf.following IS NOT NULL" in sql
    assert args[4] == "https://example.com/actors/alice"


@pytest.mark.asyncio
async def test_fetch_keeps_the_helper_queries_inlined(fake_pool, fake_conn):
    fake_conn.fetch.return_value = []

    await (await user_timeline.storage()).fetch("alice")

    sql = fake_conn.fetch.await_args.args[0]
    assert "private_access AS NOT MATERIALIZED" in sql
    assert "follows AS NOT MATERIALIZED" in sql

