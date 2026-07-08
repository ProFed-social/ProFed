# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from profed.http.client import HttpClient
 
 
def _mock_response(status_code=200, json_data=None):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_data or {}
    r.raise_for_status = MagicMock(
        side_effect=None if status_code < 400 else Exception("HTTP error"))
    return r


@pytest.mark.asyncio
async def test_get_returns_response():
    with patch("profed.http.client.httpx.AsyncClient") as mock:
        mock.return_value.__aenter__.return_value.request = \
            AsyncMock(return_value=_mock_response())
        response = await HttpClient().get("https://example.com/")

    assert response.status_code == 200


@pytest.mark.asynci
async def test_raises_on_http_error():
     with patch("profed.http.client.httpx.AsyncClient") as mock:
         mock.return_value.__aenter__.return_value.request = \
             AsyncMock(return_value=_mock_response(status_code=404))
         with pytest.raises(Exception):
            await HttpClient().get("https://example.com/")


@pytest.mark.asyncio
async def test_raise_for_status_false_returns_error_response():
     with patch("profed.http.client.httpx.AsyncClient") as mock:
         mock.return_value.__aenter__.return_value.request = \
            AsyncMock(return_value=_mock_response(status_code=404))
         response = await HttpClient().get("https://example.com/", raise_for_status=False)

     assert response.status_code == 404


@pytest.mark.asyncio
async def test_post_passes_method_correctly():
     with patch("profed.http.client.httpx.AsyncClient") as mock:
         request_mock = AsyncMock(return_value=_mock_response())
         mock.return_value.__aenter__.return_value.request = request_mock
         await HttpClient().post("https://example.com/", json={"x": 1})
 
     assert request_mock.call_args[0][0] == "POST"


@pytest.mark.asyncio
async def test_follows_redirects():
     with patch("profed.http.client.httpx.AsyncClient") as mock_cls:
         mock_cls.return_value.__aenter__.return_value.request = \
             AsyncMock(return_value=_mock_response())
         await HttpClient().get("https://example.com/")
 
     assert mock_cls.call_args.kwargs.get("follow_redirects") is True

