# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import re

import pytest
from unittest.mock import AsyncMock, Mock
import profed.components.api.c2s.shared.media.storage as module


@pytest.fixture
def fake_pool():
    conn = Mock()
    conn.execute = AsyncMock()
    conn.fetchrow = AsyncMock()
    conn.fetch = AsyncMock()
    class _Ctx:
        async def __aenter__(self): return conn
        async def __aexit__(self, *_): pass
    pool = Mock()
    pool.acquire = Mock(return_value=_Ctx())
    backup = module._instance
    module._instance = module._Storage(pool)

    yield pool

    module._instance = backup


@pytest.mark.asyncio
async def test_get_by_source_url_returns_matching_row(fake_pool):
    row = {"file_id":     "abc123",
           "url":         "https://cdn.example.com/ab/abc123",
           "source_url":  "https://example.com/photo.jpg",
           "content_hash": "deadbeef"}
    async with fake_pool.acquire() as conn:
        conn.fetchrow.return_value = row
    store  = await module.storage()

    result = await store.get_by_source_url("https://example.com/photo.jpg")

    assert result is not None
    assert result["file_id"] == "abc123"
    assert result["content_hash"] == "deadbeef"


@pytest.mark.asyncio
async def test_get_by_source_url_returns_none_when_not_found(fake_pool):
    async with fake_pool.acquire() as conn:
        conn.fetchrow.return_value = None
    store  = await module.storage()

    result = await store.get_by_source_url("https://example.com/nonexistent.jpg")

    assert result is None


@pytest.mark.asyncio
async def test_the_alt_text_is_stored_with_the_upload(fake_pool):
    async with fake_pool.acquire() as conn:
        store = await module.storage()

        await store.insert(file_id="abc123",
                           url="https://cdn.example.com/ab/abc123",
                           content_type="image/jpeg",
                           size=4711,
                           uploader="alice@example.com",
                           description="Ein Diagramm")

    sql, *args = conn.execute.await_args.args
    assert re.search(r"INSERT\s+INTO\s+api\.media", sql)
    assert "description" in sql
    assert "Ein Diagramm" in args


@pytest.mark.asyncio
async def test_owned_media_comes_back_for_the_uploader(fake_pool):
    rows = [{"file_id": "a",
             "url": "https://cdn.example.com/a",
             "content_type": "image/jpeg",
             "description": "Erstes",
             "width": 800,
             "height": 600}]
    async with fake_pool.acquire() as conn:
        conn.fetch.return_value = rows
    store = await module.storage()

    result = await store.owned_by(["a"], "alice@example.com")

    assert result == rows


@pytest.mark.asyncio
async def test_the_lookup_asks_for_the_uploader_as_well_as_the_ids(fake_pool):
    async with fake_pool.acquire() as conn:
        conn.fetch.return_value = []
        store = await module.storage()

        await store.owned_by(["a", "b"], "alice@example.com")

    sql, *args = conn.fetch.await_args.args
    assert re.search(r"WHERE\s+file_id\s*=\s*ANY", sql)
    assert "uploader" in sql
    assert args == [["a", "b"], "alice@example.com"]


@pytest.mark.asyncio
async def test_no_ids_means_no_query(fake_pool):
    async with fake_pool.acquire() as conn:
        store = await module.storage()

        assert await store.owned_by([], "alice@example.com") == []

    conn.fetch.assert_not_awaited()

