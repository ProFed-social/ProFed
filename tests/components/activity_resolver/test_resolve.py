# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, patch
from profed.components.activity_resolver import resolve
from profed.components.activity_resolver.resolve import resolve_object


@pytest.mark.asyncio
async def test_same_origin_embed_is_trusted_without_fetch():
    embedded = {"id": "https://trusted.example/notes/1", "type": "Note", "content": "hi"}

    with patch.object(resolve, "_fetch", AsyncMock()) as fetch:
        result = await resolve_object(embedded, "trusted.example")

    fetch.assert_not_called()
    assert result["content"] == "hi"


@pytest.mark.asyncio
async def test_anonymous_embed_is_trusted_without_fetch():
    embedded = {"type": "Note", "content": "hi"}

    with patch.object(resolve, "_fetch", AsyncMock()) as fetch:
        result = await resolve_object(embedded, "trusted.example")

    fetch.assert_not_called()
    assert result["content"] == "hi"


@pytest.mark.asyncio
async def test_cross_origin_embed_is_refetched_from_its_id():
    embedded = {"id": "https://other.example/notes/1", "type": "Note", "content": "FAKE"}
    real = {"id": "https://other.example/notes/1", "type": "Note", "content": "REAL"}

    with patch.object(resolve, "_fetch", AsyncMock(return_value=real)) as fetch:
        result = await resolve_object(embedded, "trusted.example")

    fetch.assert_awaited_once_with("https://other.example/notes/1")
    assert result["content"] == "REAL"


@pytest.mark.asyncio
async def test_uri_reference_is_fetched():
    real = {"id": "https://other.example/notes/1", "type": "Note", "content": "REAL"}

    with patch.object(resolve, "_fetch", AsyncMock(return_value=real)):
        result = await resolve_object("https://other.example/notes/1", "trusted.example")

    assert result["content"] == "REAL"


@pytest.mark.asyncio
async def test_fetch_failure_falls_back_to_uri():
    with patch.object(resolve, "_fetch", AsyncMock(return_value=None)):
        result = await resolve_object("https://other.example/notes/1", "trusted.example")

    assert result == "https://other.example/notes/1"


@pytest.mark.asyncio
async def test_spoofed_fetch_response_falls_back_to_uri():
    spoof = {"id": "https://evil.example/x", "type": "Note", "content": "bad"}

    with patch.object(resolve, "_fetch", AsyncMock(return_value=spoof)):
        result = await resolve_object("https://good.example/notes/1", "trusted.example")

    assert result == "https://good.example/notes/1"


@pytest.mark.asyncio
async def test_resolved_content_is_sanitised():
    embedded = {"id": "https://trusted.example/notes/1", "type": "Note",
                "content": "<script>alert(1)</script>hi"}

    result = await resolve_object(embedded, "trusted.example")

    assert "<script>" not in result["content"]


@pytest.mark.asyncio
async def test_fetch_returns_none_on_http_error():
    with patch.object(resolve, "HttpClient") as client:
        client.return_value.get = AsyncMock(side_effect=Exception("boom"))

        assert await resolve._fetch("https://x.example/1") is None

