# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timezone
import pytest
from unittest.mock import AsyncMock, Mock
from profed.components.account_resolver.storage import _Storage


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
async def test_ensure_schema_creates_both_tables(store, fake_conn):
    await store.ensure_schema()

    statements = " ".join(call.args[0] for call in fake_conn.execute.await_args_list)
    assert "account_resolver.process" in statements
    assert "account_resolver.request" in statements


@pytest.mark.asyncio
async def test_a_process_is_keyed_by_source_and_sequence(store, fake_conn):
    await store.record_process("unknown_actors", 7, "alice@a.test", "attempting", NOW)

    sql, *args = fake_conn.execute.await_args.args
    assert "INSERT INTO account_resolver.process" in sql
    assert "ON CONFLICT (source, sequence_id) DO UPDATE" in sql
    assert args == ["unknown_actors", 7, "alice@a.test", "attempting", NOW]


@pytest.mark.asyncio
async def test_recording_a_process_keeps_its_entry(store, fake_conn):
    await store.record_process("unknown_actors", 7, "alice@a.test", "resolved", NOW)

    assert "SET state" in fake_conn.execute.await_args.args[0]
    assert "entry" not in fake_conn.execute.await_args.args[0].split("DO UPDATE")[1]


@pytest.mark.asyncio
async def test_a_request_is_keyed_by_process_kind_and_ordinal(store, fake_conn):
    await store.record_request("unknown_actors", 7, "jrd", 1, "attempting", 1, "alice@a.test", None, NOW)

    sql, *args = fake_conn.execute.await_args.args
    assert "INSERT INTO account_resolver.request" in sql
    assert "ON CONFLICT (source, sequence_id, kind, ordinal) DO UPDATE" in sql
    assert args == ["unknown_actors", 7, "jrd", 1, "attempting", 1, "alice@a.test", None, NOW]
    assert "first_attempt_at" in sql


@pytest.mark.asyncio
async def test_a_later_attempt_does_not_erase_the_document(store, fake_conn):
    await store.record_request("unknown_actors", 7, "jrd", 1, "request_failed", 2, "a@b", None, NOW)

    assert "COALESCE(excluded.document, " in fake_conn.execute.await_args.args[0]


@pytest.mark.asyncio
async def test_a_later_attempt_keeps_the_first_attempt_time(store, fake_conn):
    await store.record_request("unknown_actors", 7, "jrd", 1, "request_failed", 2, "a@b", None, NOW)

    sql = fake_conn.execute.await_args.args[0]
    assert "COALESCE(account_resolver.request.first_attempt_at," in sql


@pytest.mark.asyncio
async def test_the_process_is_read_by_source_and_sequence(store, fake_conn):
    fake_conn.fetchrow.return_value = {"entry": "alice@a.test", "state": "attempting"}

    result = await store.process("unknown_actors", 7)

    sql, *args = fake_conn.fetchrow.await_args.args
    assert "FROM account_resolver.process" in sql
    assert args == ["unknown_actors", 7]
    assert result["entry"] == "alice@a.test"


@pytest.mark.asyncio
async def test_an_unknown_process_is_none(store, fake_conn):
    assert await store.process("unknown_actors", 7) is None


@pytest.mark.asyncio
async def test_the_requests_of_a_process_come_in_numeric_order(store, fake_conn):
    fake_conn.fetch.return_value = [{"kind": "jrd", "ordinal": 2}, {"kind": "jrd", "ordinal": 10}]

    result = await store.requests("unknown_actors", 7)

    sql, *args = fake_conn.fetch.await_args.args
    assert "FROM account_resolver.request" in sql
    assert "ORDER BY kind, ordinal" in sql
    assert args == ["unknown_actors", 7]
    assert [row["ordinal"] for row in result] == [2, 10]


@pytest.mark.asyncio
async def test_unfinished_skips_the_closed_processes(store, fake_conn):
    fake_conn.fetch.return_value = [{"source": "unknown_actors", "sequence_id": 9, "entry": "bob@b.test"}]

    result = await store.unfinished()

    sql = fake_conn.fetch.await_args.args[0]
    assert "WHERE state NOT IN ('resolved', 'unresolved')" in sql
    assert result[0]["entry"] == "bob@b.test"

