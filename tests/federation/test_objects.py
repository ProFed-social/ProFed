# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import AsyncMock, MagicMock, patch
from profed.federation.objects import fetch_object


async def test_fetch_object_returns_the_fetched_document():
    with patch("profed.federation.objects.HttpClient") as client:
        client.return_value.get = AsyncMock(return_value=MagicMock(json=MagicMock(return_value={"id": "x"})))

        assert await fetch_object("https://r.example/notes/1") == {"id": "x"}


async def test_fetch_object_requests_activity_json_and_passes_sign():
    sign = object()

    with patch("profed.federation.objects.HttpClient") as client:
        client.return_value.get = AsyncMock(return_value=MagicMock(json=MagicMock(return_value={})))
        await fetch_object("https://r.example/notes/1", sign)

    assert client.return_value.get.call_args.kwargs["sign"] is sign
    assert client.return_value.get.call_args.kwargs["headers"]["Accept"] == "application/activity+json"


async def test_fetch_object_returns_none_on_error():
    with patch("profed.federation.objects.HttpClient") as client:
        client.return_value.get = AsyncMock(side_effect=Exception("boom"))

        assert await fetch_object("https://r.example/notes/1") is None

