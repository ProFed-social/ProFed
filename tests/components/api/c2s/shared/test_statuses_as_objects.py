# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, Mock
from profed.components.api.c2s.shared.statuses import as_objects


@pytest.fixture
def fake_conn():
    conn = Mock()
    conn.execute = AsyncMock()
    conn.fetchrow = AsyncMock()
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
    backup = as_objects._instance
    as_objects._instance = as_objects._storage(pool)

    yield pool

    as_objects._instance = backup


@pytest.mark.asyncio
async def test_ensure_schema_creates_table_function_view_and_compression_function(fake_pool, fake_conn):
    await (await as_objects.storage()).ensure_schema()

    statements = [call.args[0] for call in fake_conn.execute.await_args_list]

    assert fake_conn.execute.await_count == 12
    assert any("CREATE TABLE" in s for s in statements)
    assert any("jsonb_build_object('status', status, 'actor', actor_url)" in s for s in statements)
    assert any("CREATE OR REPLACE FUNCTION api.resolve_content" in s and "CYCLE url SET is_cycle" in s
               for s in statements)
    assert any("CREATE OR REPLACE VIEW api.reblog_compression" in s and "LEAST(b.mastodon_id, c.mastodon_id)" in s
               for s in statements)
    assert any("CREATE TYPE api.reblog_compression_kind AS ENUM" in s for s in statements)
    assert any("CREATE OR REPLACE FUNCTION\n" in s and "api.compress_reblogs" in s for s in statements)
    assert any("CREATE OR REPLACE FUNCTION api.ancestor_chain" in s and
               "NOT break_on_author OR p.actor_url = c.actor_url" in s
               for s in statements)
    assert any("CREATE OR REPLACE FUNCTION api.find_root" in s for s in statements)
    assert any("CREATE OR REPLACE FUNCTION api.thread_root" in s and
               "api.find_root(start_url, max_depth, true)" in s
               for s in statements)
    assert any("CREATE OR REPLACE FUNCTION api.discussion_root" in s and
               "api.find_root(start_url, max_depth, false)" in s
               for s in statements)
    assert any("CREATE OR REPLACE FUNCTION api.content_url" in s for s in statements)


@pytest.mark.asyncio
async def test_upsert_inserts_the_object(fake_pool, fake_conn):
    await (await as_objects.storage()).upsert("42", "https://r/1", "https://r/bob", {"id": "42"}, None)

    sql, *args = fake_conn.execute.await_args.args
    assert "INSERT INTO api.as_objects" in sql
    assert "ON CONFLICT (url) DO NOTHING" in sql
    assert args == ["42", "https://r/1", "https://r/bob", {"id": "42"}, None]


@pytest.mark.asyncio
async def test_upsert_keeps_the_reblog_of_url(fake_pool, fake_conn):
    await (await as_objects.storage()).upsert("43", "https://r/boost", "https://r/carol", {"id": "43"}, "https://r/1")

    assert fake_conn.execute.await_args.args[5] == "https://r/1"


@pytest.mark.asyncio
async def test_update_content_writes_status_and_edited_at_only(fake_pool, fake_conn):
    store = await as_objects.storage()

    await store.update_content("https://r/1", {"id": "42", "content": "neu"}, "2026-05-01T00:00:00Z")

    sql, *args = fake_conn.execute.await_args.args
    assert "UPDATE api.as_objects" in sql
    assert "mastodon_id" not in sql
    assert args == ["https://r/1", {"id": "42", "content": "neu"}, "2026-05-01T00:00:00Z"]


@pytest.mark.asyncio
async def test_delete_removes_the_object(fake_pool, fake_conn):
    await (await as_objects.storage()).delete("https://r/1")

    sql, *args = fake_conn.execute.await_args.args
    assert "DELETE FROM api.as_objects" in sql
    assert args == ["https://r/1"]


@pytest.mark.asyncio
async def test_get_resolves_the_content_via_the_function(fake_pool, fake_conn):
    fake_conn.fetchrow.return_value = {"mastodon_id": 42,
                                       "url": "https://r/boost",
                                       "reblog_of_url": "https://r/1",
                                       "status": {"id": "42"},
                                       "content": {"id": "1", "content": "ziel"}}

    result = await (await as_objects.storage()).get("42", 20)

    sql, *args = fake_conn.fetchrow.await_args.args
    assert "api.resolve_content(url, $2)" in sql
    assert args == ["42", 20]
    assert result["content"] == {"id": "1", "content": "ziel"}


@pytest.mark.asyncio
async def test_get_returns_none_when_absent(fake_pool, fake_conn):
    fake_conn.fetchrow.return_value = None
    assert await (await as_objects.storage()).get("42", 20) is None


@pytest.mark.asyncio
async def test_fetch_by_actor_resolves_filters_unresolved_and_paginates(fake_pool, fake_conn):
    fake_conn.fetch.return_value = [{"mastodon_id": 43, "content": {"id": "x"}}]

    result = await (await as_objects.storage()).fetch_by_actor("https://r/bob", limit=5, max_id="99", max_depth=10)

    sql, *args = fake_conn.fetch.await_args.args
    assert "CROSS JOIN LATERAL" in sql
    assert "api.resolve_content(o.url, $5)" in sql
    assert "r.content IS NOT NULL" in sql
    assert "o.actor_url, o.reblog_of_url" in sql
    assert "ORDER BY o.mastodon_id DESC" in sql
    assert args == ["https://r/bob", 5, "99", None, 10]
    assert [row["mastodon_id"] for row in result] == [43]


async def test_mastodon_ids_for_maps_urls_to_string_ids(fake_pool, fake_conn):
    fake_conn.fetch.return_value = [{"url": "https://x/1", "mastodon_id": 11},
                                    {"url": "https://x/2", "mastodon_id": 22}]

    result = await (await as_objects.storage()).mastodon_ids_for(["https://x/1", "https://x/2"])

    sql, *args = fake_conn.fetch.await_args.args
    assert "mastodon_id" in sql
    assert "ANY($1" in sql
    assert args == [["https://x/1", "https://x/2"]]
    assert result == {"https://x/1": "11", "https://x/2": "22"}


@pytest.mark.asyncio
async def test_compress_chains_calls_the_function_for_heads_and_returns_the_count(fake_pool, fake_conn):
    fake_conn.fetchrow.return_value = {"changed": 3}

    result = await (await as_objects.storage()).compress_chains()

    assert "api.compress_reblogs('chain')" in fake_conn.fetchrow.await_args.args[0]
    assert result == 3


@pytest.mark.asyncio
async def test_compress_cycles_calls_the_function_with_the_sample_size_and_returns_the_count(fake_pool, fake_conn):
    fake_conn.fetchrow.return_value = {"changed": 2}

    result = await (await as_objects.storage()).compress_cycles(10)

    sql, *args = fake_conn.fetchrow.await_args.args
    assert "api.compress_reblogs('cycle', $1)" in sql
    assert args == [10]
    assert result == 2


@pytest.mark.asyncio
async def test_compress_all_sums_the_chain_and_cycle_counts(fake_pool, fake_conn):
    fake_conn.fetchrow.side_effect = [{"changed": 3}, {"changed": 2}]

    assert await (await as_objects.storage()).compress_all(10) == 5


@pytest.mark.asyncio
async def test_thread_of_walks_same_author_replies_ordered_and_resolved(fake_pool, fake_conn):
    fake_conn.fetch.return_value = [{"url": "https://r/a1", "content": {"id": "1"}},
                                    {"url": "https://r/a2", "content": {"id": "2"}}]

    result = await (await as_objects.storage()).thread_of("https://r/a1", max_depth=10)

    sql, *args = fake_conn.fetch.await_args.args
    assert "WITH RECURSIVE thread" in sql
    assert "c.status->>'in_reply_to_id' = t.url" in sql
    assert "c.actor_url = t.actor_url" in sql
    assert "api.resolve_content(o.url, $2)" in sql
    assert "ORDER BY" in sql and "th.sortkey" in sql
    assert args == ["https://r/a1", 10, True]
    assert [row["url"] for row in result] == ["https://r/a1", "https://r/a2"]


@pytest.mark.asyncio
async def test_boosted_parts_returns_the_thread_urls_the_booster_boosted(fake_pool, fake_conn):
    fake_conn.fetch.return_value = [{"boosted_part": "https://r/a2"}, {"boosted_part": "https://r/a4"}]

    result = await (await as_objects.storage()).boosted_parts("https://r/x",
                                                              ["https://r/a1", "https://r/a2", "https://r/a4"],
                                                              max_depth=10)

    sql, *args = fake_conn.fetch.await_args.args
    assert "api.content_url(o.url, $3)" in sql
    assert "o.reblog_of_url IS NOT NULL" in sql
    assert "ANY($2::text[])" in sql
    assert args == ["https://r/x", ["https://r/a1", "https://r/a2", "https://r/a4"], 10]
    assert result == ["https://r/a2", "https://r/a4"]


@pytest.mark.asyncio
async def test_discussion_of_walks_all_authors_via_break_flag(fake_pool, fake_conn):
    fake_conn.fetch.return_value = [{"url": "https://r/root", "content": {"id": "1"}}]

    await (await as_objects.storage()).discussion_of("https://r/root", max_depth=10)

    sql, *args = fake_conn.fetch.await_args.args
    assert "WITH RECURSIVE thread" in sql
    assert "NOT $3::boolean OR c.actor_url = t.actor_url" in sql
    assert args == ["https://r/root", 10, False]


@pytest.mark.asyncio
async def test_discussion_ancestors_joins_ancestor_chain_without_the_status_itself(fake_pool, fake_conn):
    fake_conn.fetch.return_value = [{"url": "https://r/root", "content": {"id": "1"}}]

    await (await as_objects.storage()).discussion_ancestors("https://r/leaf", max_depth=10)

    sql, *args = fake_conn.fetch.await_args.args
    assert "api.ancestor_chain($1, $2, $3::boolean)" in sql
    assert "a.depth > 1" in sql
    assert "ORDER BY\n                a.depth DESC" in sql
    assert args == ["https://r/leaf", 10, False]


@pytest.mark.asyncio
async def test_rows_for_urls_fetches_rows_for_a_url_list(fake_pool, fake_conn):
    fake_conn.fetch.return_value = [{"url": "https://x/1", "content": {"id": "1"}}]

    await (await as_objects.storage()).rows_for_urls(["https://x/1", "https://x/2"], 20)

    sql, *args = fake_conn.fetch.await_args.args
    assert "api.resolve_content(url, $2)" in sql
    assert "WHERE url = ANY($1::text[])" in sql
    assert args == [["https://x/1", "https://x/2"], 20]


@pytest.mark.asyncio
async def test_url_for_author_returns_the_url_of_the_authors_own_object(fake_pool, fake_conn):
    fake_conn.fetchrow.return_value = {"url": "https://example.com/actors/alice/notes/1"}
 
    result = await (await as_objects.storage()).url_for_author("424242", "https://example.com/actors/alice")
 
    sql, *args = fake_conn.fetchrow.await_args.args
    assert "WHERE mastodon_id = $1::numeric" in sql
    assert "AND actor_url = $2" in sql
    assert args == ["424242", "https://example.com/actors/alice"]
    assert result == "https://example.com/actors/alice/notes/1"
 
 
@pytest.mark.asyncio
async def test_url_for_author_returns_none_for_a_foreign_object(fake_pool, fake_conn):
    fake_conn.fetchrow.return_value = None
 
    assert await (await as_objects.storage()).url_for_author("500", "https://example.com/actors/alice") is None

