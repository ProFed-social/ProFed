# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from profed.components.client.paging import fetched, next_query


def _response(link=None):
    return SimpleNamespace(headers={"Link": link} if link else {})


def test_the_query_of_the_next_page_is_handed_on():
    link = ('<https://test.local/api/v1/bookmarks?limit=20&max_id=400>; rel="next", '
            '<https://test.local/api/v1/bookmarks?limit=20&since_id=500>; rel="prev"')

    assert next_query(_response(link)) == "limit=20&max_id=400"


def test_a_page_without_a_link_header_has_no_next():
    assert next_query(_response()) is None


def test_a_header_with_only_a_previous_page_has_no_next():
    assert next_query(_response('<https://test.local/x?since_id=5>; rel="prev"')) is None


def test_a_next_without_a_query_has_nothing_to_hand_on():
    assert next_query(_response('<https://test.local/api/v1/bookmarks>; rel="next"')) is None


def test_the_path_of_the_next_page_is_not_handed_on():
    link = '<https://elsewhere.example/other/path?max_id=400>; rel="next"'

    assert next_query(_response(link)) == "max_id=400"


def _api(status=200, rows=None, link=None):
    response = Mock(status_code=status, text="", headers={"Link": link} if link else {})
    response.json = Mock(return_value=rows)
    return lambda: Mock(get=AsyncMock(return_value=response))


async def test_a_page_comes_back_with_the_query_of_the_next_one():
    api = _api(200, [{"id": "1"}], "<https://test.local/api/v1/bookmarks?limit=20&max_id=400>; rel=\"next\"")

    assert await fetched(api, "/api/v1/bookmarks", "limit=20", "tok", "bookmarks") == \
        ([{"id": "1"}], "limit=20&max_id=400")


async def test_the_query_reaches_the_api_unchanged():
    api = _api(200, [])
    client = api()

    await fetched(lambda: client, "/api/v1/bookmarks", "limit=20&max_id=400", "tok", "bookmarks")

    assert client.get.call_args.kwargs["params"] == "limit=20&max_id=400"
    assert client.get.call_args.kwargs["token"] == "tok"


async def test_a_refused_page_is_empty_and_leads_nowhere():
    assert await fetched(_api(503), "/api/v1/bookmarks", "limit=20", "tok", "bookmarks") == ([], None)

