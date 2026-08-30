# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import Mock
from profed.components.me_links.fetch import classify, conditional_headers, me_links_of, points_back


PROFILE = "https://p.test/@alice"


def _response(status, text="", headers=None, content=b""):
    return Mock(status_code=status,
                is_success=200 <= status < 300,
                text=text,
                content=content or text.encode(),
                headers=headers or {})


def _page(*links):
    return "<html><body>" + "".join(f'<a rel="me" href="{link}">me</a>' for link in links) + "</body></html>"


def test_a_page_without_rel_me_has_no_links():
    assert me_links_of("<html><body><a href='/x'>x</a></body></html>", "https://a.test/") == []


def test_a_rel_me_link_is_found():
    assert me_links_of(_page(PROFILE), "https://a.test/") == [PROFILE]


def test_broken_markup_yields_no_links():
    assert me_links_of(None, "https://a.test/") == []


def test_a_matching_link_points_back():
    assert points_back([PROFILE], PROFILE) is True


def test_a_trailing_slash_still_points_back():
    assert points_back([PROFILE + "/"], PROFILE) is True


def test_another_scheme_does_not_point_back():
    assert points_back(["http://p.test/@alice"], PROFILE) is False


def test_another_profile_does_not_point_back():
    assert points_back(["https://p.test/@bob"], PROFILE) is False


def test_no_links_do_not_point_back():
    assert points_back([], PROFILE) is False


def test_a_missing_page_is_gone():
    assert classify(_response(404), "https://a.test/").state == "gone"


def test_a_removed_page_is_gone():
    assert classify(_response(410), "https://a.test/").state == "gone"


def test_an_unmodified_page_is_unchanged():
    assert classify(_response(304), "https://a.test/").state == "unchanged"


def test_a_server_error_is_a_failure():
    assert classify(_response(500), "https://a.test/").state == "failed"


def test_a_readable_page_is_read():
    assert classify(_response(200, _page(PROFILE)), "https://a.test/").state == "read"


def test_a_read_page_carries_its_links():
    assert classify(_response(200, _page(PROFILE)), "https://a.test/").links == [PROFILE]


def test_a_read_page_carries_its_freshness_headers():
    headers = {"last-modified": "Sat, 30 Aug 2026 08:00:00 GMT", "etag": '"abc"'}

    page = classify(_response(200, _page(PROFILE), headers), "https://a.test/")

    assert page.last_modified == "Sat, 30 Aug 2026 08:00:00 GMT"
    assert page.etag == '"abc"'


def test_a_read_page_is_hashed():
    first = classify(_response(200, _page(PROFILE)), "https://a.test/").content_hash
    second = classify(_response(200, _page("https://p.test/@bob")), "https://a.test/").content_hash

    assert first != second


def test_without_previous_knowledge_no_conditional_headers_are_sent():
    assert conditional_headers(None) == {}


def test_a_known_etag_becomes_if_none_match():
    assert conditional_headers({"etag": '"abc"'}) == {"If-None-Match": '"abc"'}


def test_a_known_date_becomes_if_modified_since():
    known = {"last_modified": "Sat, 30 Aug 2026 08:00:00 GMT"}

    assert conditional_headers(known) == {"If-Modified-Since": "Sat, 30 Aug 2026 08:00:00 GMT"}

