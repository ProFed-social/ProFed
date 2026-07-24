# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import mf2py
from profed.components.client.templating import STANDARD_TEMPLATES, build_environment
from profed.components.profile_importer.normalizer import normalize_mf2_to_profile


STATUS = {"content": "<p>Hallo Welt</p>",
          "created_at": "2026-01-01T10:00:00.000Z",
          "url": "https://example.com/@alice/1",
          "uri": "https://example.com/actors/alice/notes/1",
          "reblogs_count": 0,
          "favourites_count": 0,
          "tags": [],
          "account": {"url": "https://example.com/@alice",
                      "acct": "alice",
                      "display_name": "Alice",
                      "username": "alice",
                      "avatar": ""}}

ACCOUNT = {"username": "alice",
           "acct": "alice",
           "display_name": "Alice",
           "url": "https://example.com/@alice",
           "note": "<p>Entwicklerin</p>",
           "avatar": "",
           "header": "",
           "created_at": "2026-01-01T00:00:00.000Z",
           "followers_count": 1,
           "following_count": 2,
           "statuses_count": 3,
           "fields": [],
           "resume": None}


def _parse_home(statuses):
    environment = build_environment(STANDARD_TEMPLATES, None)
    return mf2py.parse(doc=environment.get_template("home.html").render(statuses=statuses))


def _feeds(parsed):
    return [item for item in parsed["items"] if "h-feed" in item["type"]]


def test_the_timeline_is_a_top_level_h_feed():
    assert len(_feeds(_parse_home([STATUS]))) == 1


def test_the_timeline_lists_its_statuses_as_children():
    feed = _feeds(_parse_home([STATUS, STATUS]))[0]

    assert [child["type"] for child in feed["children"]] == [["h-entry"], ["h-entry"]]


def test_an_empty_timeline_has_no_entries():
    feed = _feeds(_parse_home([]))[0]

    assert feed.get("children", []) == []


def test_the_timeline_entries_keep_their_content():
    feed = _feeds(_parse_home([STATUS]))[0]

    assert "Hallo Welt" in feed["children"][0]["properties"]["content"][0]["html"]


def test_the_timeline_entries_carry_their_permalink():
    feed = _feeds(_parse_home([STATUS]))[0]

    assert feed["children"][0]["properties"]["url"] == ["https://example.com/@alice/1"]


def _parse_profile(statuses):
    environment = build_environment(STANDARD_TEMPLATES, None)
    html = environment.get_template("profile.html").render(account=ACCOUNT,
                                                           statuses=statuses,
                                                           handle="alice",
                                                           relationship=None)
    return mf2py.parse(doc=html)


def test_the_profile_feed_is_a_top_level_h_feed():
    assert len(_feeds(_parse_profile([STATUS]))) == 1


def test_the_profile_card_stays_a_top_level_h_card():
    parsed = _parse_profile([STATUS])

    assert any("h-card" in item["type"] for item in parsed["items"])


def test_the_profile_feed_is_not_nested_inside_the_card():
    card = next(item for item in _parse_profile([STATUS])["items"] if "h-card" in item["type"])

    assert not any("h-feed" in child["type"] for child in card.get("children", []))


def test_the_profile_feed_lists_its_statuses_as_children():
    feed = _feeds(_parse_profile([STATUS, STATUS]))[0]

    assert [child["type"] for child in feed["children"]] == [["h-entry"], ["h-entry"]]


def test_the_profile_feed_omits_the_repeated_author():
    feed = _feeds(_parse_profile([STATUS]))[0]

    assert feed["children"][0]["properties"].get("author") is None


def test_the_profile_page_can_be_read_by_the_own_importer():
    assert normalize_mf2_to_profile(_parse_profile([STATUS])) is not None

