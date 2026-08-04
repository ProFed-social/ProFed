# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from profed.components.activity_resolver.storage import _Storage


AT = datetime(2026, 4, 1, tzinfo=timezone.utc)
VERSION = datetime(2026, 1, 1, tzinfo=timezone.utc)
CACHE_END = datetime(2026, 1, 1, 1, tzinfo=timezone.utc)


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
async def test_record_process_upserts_without_touching_version(store, fake_conn):
    await store.record_process("https://x/1", "attempting", AT, 2, 0)
    sql, *args = fake_conn.execute.call_args[0]

    assert "INSERT INTO activity_resolver.resolution" in sql
    assert "ON CONFLICT (object_id) DO UPDATE" in sql
    assert "version" not in sql.split("DO UPDATE")[1]
    assert args == ["https://x/1", "attempting", AT, 2, 0]


@pytest.mark.asyncio
async def test_record_version_guards_the_update_against_older_versions(store, fake_conn):
    await store.record_version("https://x/1", "succeeded", VERSION, CACHE_END, AT, 0, 0)
    sql, *args = fake_conn.execute.call_args[0]

    assert "ON CONFLICT (object_id) DO UPDATE" in sql
    assert "version         = excluded.version" in sql
    assert "cache_end       = excluded.cache_end" in sql
    assert "WHERE activity_resolver.resolution.version IS NULL" in sql
    assert "excluded.version >= activity_resolver.resolution.version" in sql
    assert args == ["https://x/1", "succeeded", VERSION, CACHE_END, AT, 0, 0]


@pytest.mark.asyncio
async def test_get_reads_the_row(store, fake_conn):
    row = {"object_id": "https://x/1",
           "state": "succeeded",
           "version": VERSION,
           "cache_end": CACHE_END,
           "emitted_at": AT,
           "attempt": 0,
           "not_found_count": 0}
    fake_conn.fetchrow = AsyncMock(return_value=row)

    result = await store.get("https://x/1")
    sql, *args = fake_conn.fetchrow.call_args[0]

    assert "SELECT" in sql and "FROM activity_resolver.resolution" in sql
    assert args == ["https://x/1"]
    assert result == row

