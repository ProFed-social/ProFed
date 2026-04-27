# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from profed.http.client import http
 
 
def _mock_response(status_code=200, json_data=None):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_data or {}
    r.raise_for_status = MagicMock(
        side_effect=None if status_code < 400 else Exception("HTTP error"))
    return r
 
 
@pytest.mark.asyncio
async def test_request_returns_response():
    with patch("profed.http.client.httpx.AsyncClient") as mock:
        mock.return_value.__aenter__.return_value.request = \
            AsyncMock(return_value=_mock_response())
        response = await http("GET").request("https://example.com/")

    assert response.status_code == 200
 
 
@pytest.mark.asyncio
async def test_request_raises_on_http_error():
    with patch("profed.http.client.httpx.AsyncClient") as mock:
        mock.return_value.__aenter__.return_value.request = \
            AsyncMock(return_value=_mock_response(status_code=404))
        with pytest.raises(Exception):
            await http("GET").request("https://example.com/")
 
 
@pytest.mark.asyncio
async def test_json_returns_parsed_json():
    with patch("profed.http.client.httpx.AsyncClient") as mock:
        mock.return_value.__aenter__.return_value.request = \
            AsyncMock(return_value=_mock_response(json_data={"key": "value"}))
        result = await http("GET").json("https://example.com/")

    assert result == {"key": "value"}
 
 
@pytest.mark.asyncio
async def test_request_passes_method_correctly():
    with patch("profed.http.client.httpx.AsyncClient") as mock:
        request_mock = AsyncMock(return_value=_mock_response())
        mock.return_value.__aenter__.return_value.request = request_mock
        await http("POST").request("https://example.com/", json={"x": 1})

    assert request_mock.call_args[0][0] == "POST"
 
 
@pytest.mark.asyncio
async def test_request_follows_redirects():
    with patch("profed.http.client.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__.return_value.request = \
            AsyncMock(return_value=_mock_response())
        await http("GET").request("https://example.com/")

    assert mock_cls.call_args.kwargs.get("follow_redirects") is True

