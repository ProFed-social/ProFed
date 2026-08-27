# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, Mock
from profed.components.actor_extractor.storage import _Storage


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
async def test_ensure_schema_creates_the_table_and_the_acct_index(store, fake_conn):
    await store.ensure_schema()

    statements = " ".join(call.args[0] for call in fake_conn.execute.await_args_list)
    assert "CREATE TABLE IF NOT EXISTS" in statements
    assert "actor_extractor.known" in statements
    assert "CREATE INDEX IF NOT EXISTS known_acct" in statements


@pytest.mark.asyncio
async def test_upsert_writes_url_and_acct(store, fake_conn):
    await store.upsert("https://a.test/actors/alice", "alice@a.test")

    sql, *args = fake_conn.execute.await_args.args
    assert "INSERT INTO actor_extractor.known" in sql
    assert "ON CONFLICT (actor_url) DO UPDATE" in sql
    assert args == ["https://a.test/actors/alice", "alice@a.test"]


@pytest.mark.asyncio
async def test_upsert_accepts_a_missing_acct(store, fake_conn):
    await store.upsert("https://a.test/actors/alice", None)

    assert fake_conn.execute.await_args.args[2] is None


@pytest.mark.asyncio
async def test_delete_removes_by_url(store, fake_conn):
    await store.delete("https://a.test/actors/alice")

    sql, *args = fake_conn.execute.await_args.args
    assert "DELETE FROM actor_extractor.known" in sql
    assert args == ["https://a.test/actors/alice"]


@pytest.mark.asyncio
async def test_unknown_urls_returns_what_the_query_yields(store, fake_conn):
    fake_conn.fetch.return_value = [{"url": "https://c.test/actors/carol"}]

    result = await store.unknown_urls(["https://a.test/actors/alice", "https://c.test/actors/carol"])

    sql, *args = fake_conn.fetch.await_args.args
    assert "unnest($1::text[])" in sql
    assert "NOT IN (SELECT actor_url FROM actor_extractor.known)" in sql
    assert args == [["https://a.test/actors/alice", "https://c.test/actors/carol"]]
    assert result == ["https://c.test/actors/carol"]


@pytest.mark.asyncio
async def test_unknown_accts_skips_rows_without_an_acct(store, fake_conn):
    fake_conn.fetch.return_value = [{"acct": "dave@d.test"}]

    result = await store.unknown_accts(["alice@a.test", "dave@d.test"])

    sql, *args = fake_conn.fetch.await_args.args
    assert "unnest($1::text[])" in sql
    assert "WHERE k.acct IS NOT NULL" in sql
    assert args == [["alice@a.test", "dave@d.test"]]
    assert result == ["dave@d.test"]

