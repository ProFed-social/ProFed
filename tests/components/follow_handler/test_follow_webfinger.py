# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from profed.components.follow_handler.webfinger import lookup_acct
 
 
def _mock_response(status_code=200, json_data=None):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data or {}
    response.raise_for_status = MagicMock(
        side_effect=None if status_code < 400 else Exception("HTTP error"))
    return response
 
 
@pytest.mark.asyncio
async def test_lookup_acct_success():
    with patch("profed.components.follow_handler.webfinger.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=_mock_response(json_data={"subject": "acct:alice@mastodon.social"}))
        result = await lookup_acct("https://mastodon.social/users/alice")
    assert result == "alice@mastodon.social"
 
 
@pytest.mark.asyncio
async def test_lookup_acct_no_subject_returns_none():
    with patch("profed.components.follow_handler.webfinger.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=_mock_response(json_data={}))
        result = await lookup_acct("https://mastodon.social/users/alice")
    assert result is None
 
 
@pytest.mark.asyncio
async def test_lookup_acct_http_error_returns_none():
    with patch("profed.components.follow_handler.webfinger.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=_mock_response(status_code=404))
        result = await lookup_acct("https://mastodon.social/users/alice")
    assert result is None
 
 
@pytest.mark.asyncio
async def test_lookup_acct_network_error_returns_none():
    with patch("profed.components.follow_handler.webfinger.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=Exception("network error"))
        result = await lookup_acct("https://mastodon.social/users/alice")
    assert result is None
 
 
@pytest.mark.asyncio
async def test_lookup_acct_builds_correct_webfinger_url():
    with patch("profed.components.follow_handler.webfinger.httpx.AsyncClient") as mock_client:
        get_mock = AsyncMock(
            return_value=_mock_response(json_data={"subject": "acct:alice@mastodon.social"}))
        mock_client.return_value.__aenter__.return_value.get = get_mock
        await lookup_acct("https://mastodon.social/users/alice")
    call_url = get_mock.call_args[0][0]
    assert call_url.startswith("https://mastodon.social/.well-known/webfinger")
    assert "resource=https%3A%2F%2Fmastodon.social%2Fusers%2Falice" in call_url

