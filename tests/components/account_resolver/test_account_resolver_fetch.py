# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, Mock, patch
from profed.components.account_resolver import fetch


JRD = {"subject": "acct:alice@a.test"}


def _response(status=200, payload=None):
    response = Mock()
    response.status_code = status
    response.is_success = 200 <= status < 300
    response.json = Mock(return_value=payload if payload is not None else {})
    return response


def _client(response=None, error=None):
    client = Mock()
    client.get = AsyncMock(side_effect=error) if error else AsyncMock(return_value=response)
    return patch.object(fetch, "HttpClient", Mock(return_value=client)), client


def test_the_webfinger_url_is_built_from_the_domain_of_an_acct():
    assert fetch.webfinger_url("alice@a.test") \
        == "https://a.test/.well-known/webfinger?resource=acct%3Aalice%40a.test"


def test_the_webfinger_url_of_a_url_asks_its_host():
    assert fetch.webfinger_url("https://a.test/actors/alice") \
        == "https://a.test/.well-known/webfinger?resource=https%3A%2F%2Fa.test%2Factors%2Falice"


def test_a_leading_at_is_dropped_from_the_resource():
    assert "acct%3Aalice%40a.test" in fetch.webfinger_url("@alice@a.test")


def test_a_jrd_request_goes_to_the_webfinger_endpoint():
    assert fetch.url_for("jrd", "alice@a.test").startswith("https://a.test/.well-known/webfinger")


def test_an_actor_request_goes_to_the_url_itself():
    assert fetch.url_for("actor", "https://a.test/actors/alice") == "https://a.test/actors/alice"


def test_a_successful_response_yields_its_document():
    assert fetch.classify(_response(200, JRD)) == ("request_succeeded", JRD)


def test_a_gone_response_is_a_tombstone():
    assert fetch.classify(_response(410)) == ("request_tombstone", None)


def test_a_missing_response_is_not_found():
    assert fetch.classify(_response(404)) == ("request_not_found", None)


def test_a_server_error_is_a_failure():
    assert fetch.classify(_response(500)) == ("request_failed", None)


def test_a_rate_limit_is_a_failure():
    assert fetch.classify(_response(429)) == ("request_failed", None)


@pytest.mark.asyncio
async def test_performing_a_jrd_request_asks_the_webfinger_endpoint():
    patcher, client = _client(_response(200, JRD))
    with patcher:
        result = await fetch.perform("jrd", "alice@a.test")

    assert client.get.await_args.args[0].startswith("https://a.test/.well-known/webfinger")
    assert client.get.await_args.kwargs["headers"]["Accept"] == "application/jrd+json"
    assert result == ("request_succeeded", JRD)


@pytest.mark.asyncio
async def test_performing_an_actor_request_asks_for_activity_json():
    patcher, client = _client(_response(200, {"id": "https://a.test/actors/alice"}))
    with patcher:
        await fetch.perform("actor", "https://a.test/actors/alice")

    assert client.get.await_args.kwargs["headers"]["Accept"] == "application/activity+json"


@pytest.mark.asyncio
async def test_performing_a_request_does_not_raise_on_an_error_status():
    patcher, client = _client(_response(404))
    with patcher:
        result = await fetch.perform("actor", "https://a.test/actors/alice")

    assert client.get.await_args.kwargs["raise_for_status"] is False
    assert result == ("request_not_found", None)


@pytest.mark.asyncio
async def test_a_transport_error_becomes_a_failure():
    patcher, _ = _client(error=RuntimeError("boom"))
    with patcher:
        assert await fetch.perform("jrd", "alice@a.test") == ("request_failed", None)


@pytest.mark.asyncio
async def test_the_signer_is_handed_to_the_client():
    patcher, client = _client(_response(200, JRD))
    signer = object()
    with patcher:
        await fetch.perform("jrd", "alice@a.test", signer)

    assert client.get.await_args.kwargs["sign"] is signer

