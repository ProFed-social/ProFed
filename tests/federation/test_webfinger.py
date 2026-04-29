# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from profed.federation.webfinger import lookup_acct, lookup_actor_url
 
 
ACTOR_URL = "https://mastodon.social/users/alice_{}"
ACCT      = "alice_{}@mastodon.social"
 
 
def _mock_response(status_code=200, json_data=None):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_data or {}
    r.raise_for_status = MagicMock(
        side_effect=None if status_code < 400 else Exception("HTTP error"))
    return r
 
 
@pytest.mark.asyncio
async def test_lookup_acct_from_actor_url():
    with patch("profed.http.client.httpx.AsyncClient") as mock:
        mock.return_value.__aenter__.return_value.request = AsyncMock(
            return_value=_mock_response(json_data={"subject": f"acct:{ACCT.format("from_actor_url")}"}))
        result = await lookup_acct(ACTOR_URL.format("from_actor_url"))
 
    assert result == ACCT.format("from_actor_url")
 
 
@pytest.mark.asyncio
async def test_lookup_acct_from_acct_string():
    with patch("profed.http.client.httpx.AsyncClient") as mock:
        mock.return_value.__aenter__.return_value.request = AsyncMock(
            return_value=_mock_response(json_data={"subject": f"acct:{ACCT.format("from_acct_string")}"}))
        result = await lookup_acct(ACCT.format("from_acct_string"))
 
    assert result == ACCT.format("from_acct_string")
 
 
@pytest.mark.asyncio
async def test_lookup_acct_no_subject_returns_none():
    with patch("profed.http.client.httpx.AsyncClient") as mock:
        mock.return_value.__aenter__.return_value.request = AsyncMock(
            return_value=_mock_response(json_data={}))
        result = await lookup_acct(ACTOR_URL.format("no_subject"))
 
    assert result is None
 
 
@pytest.mark.asyncio
async def test_lookup_acct_http_error_returns_none():
    with patch("profed.http.client.httpx.AsyncClient") as mock:
        mock.return_value.__aenter__.return_value.request = AsyncMock(
            return_value=_mock_response(status_code=404))
        result = await lookup_acct(ACTOR_URL.format("http_error"))
 
    assert result is None
 
 
@pytest.mark.asyncio
async def test_lookup_acct_network_error_returns_none():
    with patch("profed.http.client.httpx.AsyncClient") as mock:
        mock.return_value.__aenter__.return_value.request = AsyncMock(
            side_effect=Exception("network error"))
        result = await lookup_acct(ACTOR_URL.format("network_error"))
 
    assert result is None
 
 
@pytest.mark.asyncio
async def test_lookup_acct_builds_correct_url_for_actor_url():
    with patch("profed.http.client.httpx.AsyncClient") as mock:
        request_mock = AsyncMock(
            return_value=_mock_response(json_data={"subject": f"acct:{ACCT.format("url_for_actor_url")}"}))
        mock.return_value.__aenter__.return_value.request = request_mock
        await lookup_acct(ACTOR_URL.format("url_for_actor_url"))
 
    url = request_mock.call_args[0][1]
    assert url.startswith("https://mastodon.social/.well-known/webfinger")
    assert "resource=https%3A%2F%2Fmastodon.social%2Fusers%2Falice_url_for_actor_url" in url
 
 
@pytest.mark.asyncio
async def test_lookup_acct_builds_correct_url_for_acct():
    with patch("profed.http.client.httpx.AsyncClient") as mock:
        request_mock = AsyncMock(
            return_value=_mock_response(json_data={"subject": f"acct:{ACCT.format("url_for_acct")}"}))
        mock.return_value.__aenter__.return_value.request = request_mock
        await lookup_acct(ACCT.format("url_for_acct"))
 
    url = request_mock.call_args[0][1]
    assert url.startswith("https://mastodon.social/.well-known/webfinger")
    assert "resource=acct%3Aalice_url_for_acct%40mastodon.social" in url
 
 
@pytest.mark.asyncio
async def test_lookup_actor_url_returns_self_link():
    links = [{"rel":  "self",
              "type": "application/activity+json",
              "href": ACTOR_URL.format("self_link")}]
    with patch("profed.http.client.httpx.AsyncClient") as mock:
        mock.return_value.__aenter__.return_value.request = AsyncMock(
            return_value=_mock_response(json_data={"links": links}))
        result = await lookup_actor_url(ACCT.format("self_link"))
 
    assert result == ACTOR_URL.format("self_link")
 
 
@pytest.mark.asyncio
async def test_lookup_actor_url_no_self_link_returns_none():
    with patch("profed.http.client.httpx.AsyncClient") as mock:
        mock.return_value.__aenter__.return_value.request = AsyncMock(
            return_value=_mock_response(json_data={"links": []}))
        result = await lookup_actor_url(ACCT.format("no_self_link"))
 
    assert result is None
 
 
@pytest.mark.asyncio
async def test_lookup_actor_url_error_returns_none():
    with patch("profed.http.client.httpx.AsyncClient") as mock:
        mock.return_value.__aenter__.return_value.request = AsyncMock(
            side_effect=Exception("network error"))
        result = await lookup_actor_url(ACCT.format("error"))
 
    assert result is None


@pytest.mark.asyncio
async def test_lookup_acct_caches_result():
    with patch("profed.http.client.httpx.AsyncClient") as mock:
        request_mock = AsyncMock(
            return_value=_mock_response(json_data={"subject": f"acct:{ACCT.format('cache_test')}"}))
        mock.return_value.__aenter__.return_value.request = request_mock
        await lookup_acct(ACTOR_URL.format("cache_test"))
        await lookup_acct(ACTOR_URL.format("cache_test"))

    assert request_mock.call_count == 1
