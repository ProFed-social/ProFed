# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from profed.core.key_value_store import (init_key_value_store,
                                         key_value_store,
                                         _reset_key_value_store)
from profed.core.key_value_store.postgresql import _PostgresKeyValueStore


def _store_with_pool():
    pool = MagicMock()
    pool.execute = AsyncMock()
    pool.fetchrow = AsyncMock()
    return _PostgresKeyValueStore(pool), pool


@pytest.mark.asyncio
async def test_get_returns_decoded_value():
    store, pool = _store_with_pool()
    pool.fetchrow.return_value = {"value": {"token": "t", "username": "alice"}}

    assert await store.get("session:1") == {"token": "t", "username": "alice"}
    assert pool.fetchrow.await_args.args[1] == "session:1"


@pytest.mark.asyncio
async def test_get_returns_none_when_absent():
    store, pool = _store_with_pool()
    pool.fetchrow.return_value = None

    assert await store.get("session:1") is None


@pytest.mark.asyncio
async def test_get_filters_expired_rows_in_query():
    store, pool = _store_with_pool()
    pool.fetchrow.return_value = None

    await store.get("session:1")

    assert "expires_at > now()" in pool.fetchrow.await_args.args[0]


@pytest.mark.asyncio
async def test_set_passes_key_value_and_ttl():
    store, pool = _store_with_pool()

    await store.set("session:1", {"token": "t"}, 300)

    assert pool.execute.await_args.args[1:] == ("session:1", {"token": "t"}, 300)
    assert "ON CONFLICT (key) DO UPDATE" in pool.execute.await_args.args[0]


@pytest.mark.asyncio
async def test_set_without_ttl_passes_none():
    store, pool = _store_with_pool()

    await store.set("session:1", {"token": "t"})

    assert pool.execute.await_args.args[1:] == ("session:1", {"token": "t"}, None)


@pytest.mark.asyncio
async def test_delete_issues_delete():
    store, pool = _store_with_pool()

    await store.delete("session:1")

    assert "DELETE FROM key_value.entries" in pool.execute.await_args.args[0]
    assert pool.execute.await_args.args[1] == "session:1"


@pytest.mark.asyncio
async def test_cleanup_deletes_expired():
    store, pool = _store_with_pool()

    await store.cleanup()

    sql = pool.execute.await_args.args[0]
    assert "DELETE FROM key_value.entries" in sql
    assert "expires_at <= now()" in sql


@pytest.mark.asyncio
async def test_ensure_schema_creates_schema_and_table():
    conn = AsyncMock()
    acquire_cm = MagicMock()
    acquire_cm.__aenter__ = AsyncMock(return_value=conn)
    acquire_cm.__aexit__ = AsyncMock(return_value=False)
    pool = MagicMock()
    pool.acquire = MagicMock(return_value=acquire_cm)
    store = _PostgresKeyValueStore(pool)

    await store._ensure_schema()

    statements = [call.args[0] for call in conn.execute.await_args_list]
    assert any("DROP SCHEMA IF EXISTS key_value CASCADE" in s for s in statements)
    assert any("CREATE SCHEMA key_value" in s for s in statements)
    assert any("CREATE TABLE key_value.entries" in s for s in statements)


def test_key_value_store_raises_before_init():
    _reset_key_value_store()
    with pytest.raises(RuntimeError):
        key_value_store()


@pytest.mark.asyncio
async def test_init_key_value_store_selects_configured_backend():
    _reset_key_value_store()
    sentinel = object()
    with patch("profed.core.key_value_store.config",
               new=lambda: {"key_value_store": {"type": "postgresql"}}), \
         patch("profed.core.key_value_store.postgresql.init",
               new=AsyncMock(return_value=sentinel)):
        await init_key_value_store()

    assert key_value_store() is sentinel
    _reset_key_value_store()

