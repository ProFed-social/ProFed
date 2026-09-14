# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import pytest
from unittest.mock import AsyncMock, Mock, patch
from profed.components.known_servers import fetch


INDEX = {"links": [{"rel": fetch.SCHEMAS[1], "href": "https://a.test/nodeinfo/2.0"}]}

DOCUMENT = {"software": {"name": "pleroma"}, "metadata": {"features": ["pleroma_emoji_reactions"]}}


def _response(status, document=None, headers=None):
    body = json.dumps(document if document is not None else {})
    return Mock(status_code=status,
                is_success=200 <= status < 300,
                json=Mock(return_value=document),
                content=body.encode(),
                headers=headers or {})


def _fetching(*responses):
    return patch("profed.components.known_servers.fetch.HttpClient",
                 Mock(return_value=Mock(get=AsyncMock(side_effect=list(responses)))))


def test_the_newest_known_schema_wins():
    links = [{"rel": fetch.SCHEMAS[1], "href": "https://a.test/2.0"},
             {"rel": fetch.SCHEMAS[0], "href": "https://a.test/2.1"}]

    assert fetch.document_url(links) == "https://a.test/2.1"


def test_an_unknown_schema_is_ignored():
    assert fetch.document_url([{"rel": "https://example.com/other", "href": "https://a.test/x"}]) is None


def test_a_malformed_link_list_yields_no_document():
    assert fetch.document_url(None) is None
    assert fetch.document_url(["nonsense", {"rel": fetch.SCHEMAS[0]}]) is None


def test_the_features_come_out_of_the_metadata():
    assert fetch.features_of(DOCUMENT) == ["pleroma_emoji_reactions"]


def test_a_document_without_metadata_has_no_features():
    assert fetch.features_of({}) == []
    assert fetch.features_of({"metadata": "nonsense"}) == []


def test_only_strings_count_as_features():
    assert fetch.features_of({"metadata": {"features": ["a", 7, None]}}) == ["a"]


def test_a_feature_object_says_nothing():
    assert fetch.features_of({"metadata": {"features": {"pleroma_emoji_reactions": False}}}) == []


def test_the_software_name_is_read():
    assert fetch.software_of(DOCUMENT) == "pleroma"
    assert fetch.software_of({"software": "nonsense"}) is None


def test_conditional_headers_are_sent_only_when_known():
    assert fetch.conditional_headers(None) == {}
    assert fetch.conditional_headers({"etag": '"a"'}) == {"If-None-Match": '"a"'}


@pytest.mark.asyncio
async def test_a_two_step_lookup_reads_the_document():
    with _fetching(_response(200, INDEX), _response(200, DOCUMENT, {"etag": '"a"'})):
        result = await fetch.perform("a.test")

    assert result.state == "read"
    assert result.software == "pleroma"
    assert result.features == ["pleroma_emoji_reactions"]
    assert result.etag == '"a"'
    assert result.content_hash is not None


@pytest.mark.asyncio
async def test_the_document_is_asked_for_at_the_advertised_url():
    getter = AsyncMock(side_effect=[_response(200, INDEX), _response(200, DOCUMENT)])
    with patch("profed.components.known_servers.fetch.HttpClient", Mock(return_value=Mock(get=getter))):
        await fetch.perform("a.test")

    assert getter.await_args_list[0].args[0] == "https://a.test/.well-known/nodeinfo"
    assert getter.await_args_list[1].args[0] == "https://a.test/nodeinfo/2.0"


@pytest.mark.asyncio
async def test_a_host_without_a_well_known_document_is_a_definite_answer():
    with _fetching(_response(404)):
        result = await fetch.perform("a.test")

    assert result.state == "read"
    assert result.features == []


@pytest.mark.asyncio
async def test_a_well_known_document_without_a_usable_link_is_a_definite_answer():
    with _fetching(_response(200, {"links": []})):
        assert (await fetch.perform("a.test")).state == "read"


@pytest.mark.asyncio
async def test_an_unchanged_document_says_so():
    with _fetching(_response(200, INDEX), _response(304)):
        assert (await fetch.perform("a.test", {"etag": '"a"'})).state == "unchanged"


@pytest.mark.asyncio
async def test_a_server_error_is_a_failure():
    with _fetching(_response(200, INDEX), _response(503)):
        assert (await fetch.perform("a.test")).state == "failed"


@pytest.mark.asyncio
async def test_an_unreachable_host_is_a_failure():
    with patch("profed.components.known_servers.fetch.HttpClient",
               Mock(return_value=Mock(get=AsyncMock(side_effect=OSError("no route"))))):
        assert (await fetch.perform("a.test")).state == "failed"


@pytest.mark.asyncio
async def test_an_unreadable_document_still_counts_as_read():
    unreadable = _response(200, None)
    unreadable.json = Mock(side_effect=ValueError("not json"))

    with _fetching(_response(200, INDEX), unreadable):
        result = await fetch.perform("a.test")

    assert result.state == "read"
    assert result.features == []

