# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, Mock
import profed.components.api.c2s.shared.media.storage as module


@pytest.fixture
def fake_pool():
    conn = Mock()
    conn.execute  = AsyncMock()
    conn.fetchrow = AsyncMock()
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
    assert result["file_id"]      == "abc123"
    assert result["content_hash"] == "deadbeef"


@pytest.mark.asyncio
async def test_get_by_source_url_returns_none_when_not_found(fake_pool):
    async with fake_pool.acquire() as conn:
        conn.fetchrow.return_value = None
    store  = await module.storage()

    result = await store.get_by_source_url("https://example.com/nonexistent.jpg")

    assert result is None
