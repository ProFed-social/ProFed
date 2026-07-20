# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import patch, AsyncMock
from profed.components.api.c2s.v1.statuses import mentions


def test_parse_mentions_extracts_remote_handle_and_host():
    assert mentions.parse_mentions("hi @dave@remote.example and @amy@other.org!") == \
        [("dave", "remote.example"), ("amy", "other.org")]


def test_parse_mentions_extracts_bare_local_handle():
    assert mentions.parse_mentions("ping @christof please") == [("christof", None)]


def test_parse_mentions_ignores_email_addresses():
    assert mentions.parse_mentions("write to foo@bar.example about it") == []


def test_parse_mentions_deduplicates_preserving_order():
    assert mentions.parse_mentions("@a@x.org @b@y.org @a@x.org") == \
        [("a", "x.org"), ("b", "y.org")]


def test_parse_mentions_stops_at_trailing_punctuation():
    assert mentions.parse_mentions("thanks @christof! and cc @a, @b") == \
        [("christof", None), ("a", None), ("b", None)]


def test_parse_mentions_accepts_liberal_userparts():
    assert mentions.parse_mentions("cc @first.last and @a+b@host.io") == \
        [("first.last", None), ("a+b", "host.io")]


def test_parse_mentions_extracts_subdomain_host():
    assert mentions.parse_mentions("@christof@pix.okunah.de") == \
        [("christof", "pix.okunah.de")]


async def test_resolve_mentions_resolves_remote_via_webfinger():
    with patch.object(mentions, "is_local", return_value=False), \
         patch.object(mentions, "lookup_actor_url",
                      AsyncMock(return_value="https://remote.example/actors/dave")):
        tag, cc = await mentions.resolve_mentions([("dave", "remote.example")])

    assert tag == [{"type": "Mention",
                    "href": "https://remote.example/actors/dave",
                    "name": "@dave@remote.example"}]
    assert cc == ["https://remote.example/actors/dave"]


async def test_resolve_mentions_resolves_bare_local_when_account_exists():
    with patch.object(mentions, "resolve_actor", AsyncMock(return_value={"username": "christof"})), \
         patch.object(mentions, "acct_from_username", lambda h: f"{h}@example.test"), \
         patch.object(mentions, "actor_url_from_username", lambda h: f"https://example.test/actors/{h}"):
        tag, cc = await mentions.resolve_mentions([("christof", None)])

    assert tag == [{"type": "Mention",
                    "href": "https://example.test/actors/christof",
                    "name": "@christof@example.test"}]
    assert cc == ["https://example.test/actors/christof"]


async def test_resolve_mentions_drops_unresolvable_remote():
    with patch.object(mentions, "is_local", return_value=False), \
         patch.object(mentions, "lookup_actor_url", AsyncMock(return_value=None)):
        tag, cc = await mentions.resolve_mentions([("ghost", "nowhere.example")])

    assert (tag, cc) == ([], [])


async def test_resolve_mentions_drops_bare_local_when_account_missing():
    with patch.object(mentions, "resolve_actor", AsyncMock(return_value=None)), \
         patch.object(mentions, "acct_from_username", lambda h: f"{h}@example.test"), \
         patch.object(mentions, "actor_url_from_username", lambda h: f"https://example.test/actors/{h}"):
        tag, cc = await mentions.resolve_mentions([("nobody", None)])

    assert (tag, cc) == ([], [])

