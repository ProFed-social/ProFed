# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from profed.federation.webfinger import lookup_acct, lookup_actor_url


ACTOR_URL = "https://mastodon.social/users/alice"
ACCT      = "alice@mastodon.social"
 
 
def _mock_response(status_code=200, json_data=None):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_data or {}
    r.raise_for_status = MagicMock(
        side_effect=None if status_code < 400 else Exception("HTTP error"))
    return r
 
 
@pytest.mark.asyncio
async def test_lookup_acct_from_actor_url():
    with patch("profed.federation.webfinger.httpx.AsyncClient") as mock:
        mock.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=_mock_response(json_data={"subject": f"acct:{ACCT}"}))
        result = await lookup_acct(ACTOR_URL)

    assert result == ACCT
 
 
@pytest.mark.asyncio
async def test_lookup_acct_from_acct_string():
    with patch("profed.federation.webfinger.httpx.AsyncClient") as mock:
        mock.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=_mock_response(json_data={"subject": f"acct:{ACCT}"}))
        result = await lookup_acct(ACCT)

    assert result == ACCT
 
 
@pytest.mark.asyncio
async def test_lookup_acct_no_subject_returns_none():
    with patch("profed.federation.webfinger.httpx.AsyncClient") as mock:
        mock.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=_mock_response(json_data={}))
        result = await lookup_acct(ACTOR_URL)

    assert result is None
 
 
@pytest.mark.asyncio
async def test_lookup_acct_http_error_returns_none():
    with patch("profed.federation.webfinger.httpx.AsyncClient") as mock:
        mock.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=_mock_response(status_code=404))
        result = await lookup_acct(ACTOR_URL)

    assert result is None
 
 
@pytest.mark.asyncio
async def test_lookup_acct_network_error_returns_none():
    with patch("profed.federation.webfinger.httpx.AsyncClient") as mock:
        mock.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=Exception("network error"))
        result = await lookup_acct(ACTOR_URL)

    assert result is None
 
 
@pytest.mark.asyncio
async def test_lookup_acct_builds_correct_url_for_actor_url():
    with patch("profed.federation.webfinger.httpx.AsyncClient") as mock:
        get_mock = AsyncMock(
            return_value=_mock_response(json_data={"subject": f"acct:{ACCT}"}))
        mock.return_value.__aenter__.return_value.get = get_mock
        await lookup_acct(ACTOR_URL)

    url = get_mock.call_args[0][0]
    assert url.startswith("https://mastodon.social/.well-known/webfinger")
    assert "resource=https%3A%2F%2Fmastodon.social%2Fusers%2Falice" in url
 
 
@pytest.mark.asyncio
async def test_lookup_acct_builds_correct_url_for_acct():
    with patch("profed.federation.webfinger.httpx.AsyncClient") as mock:
        get_mock = AsyncMock(
            return_value=_mock_response(json_data={"subject": f"acct:{ACCT}"}))
        mock.return_value.__aenter__.return_value.get = get_mock
        await lookup_acct(ACCT)

    url = get_mock.call_args[0][0]
    assert url.startswith("https://mastodon.social/.well-known/webfinger")
    assert "resource=acct%3Aalice%40mastodon.social" in url
 
 
@pytest.mark.asyncio
async def test_lookup_actor_url_returns_self_link():
    links = [{"rel":  "self",
              "type": "application/activity+json",
              "href": ACTOR_URL}]
    with patch("profed.federation.webfinger.httpx.AsyncClient") as mock:
        mock.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=_mock_response(json_data={"links": links}))
        result = await lookup_actor_url(ACCT)

    assert result == ACTOR_URL
 
 
@pytest.mark.asyncio
async def test_lookup_actor_url_no_self_link_returns_none():
    with patch("profed.federation.webfinger.httpx.AsyncClient") as mock:
        mock.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=_mock_response(json_data={"links": []}))
        result = await lookup_actor_url(ACCT)

    assert result is None
 
 
@pytest.mark.asyncio
async def test_lookup_actor_url_error_returns_none():
    with patch("profed.federation.webfinger.httpx.AsyncClient") as mock:
        mock.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=Exception("network error"))
        result = await lookup_actor_url(ACCT)

    assert result is None

