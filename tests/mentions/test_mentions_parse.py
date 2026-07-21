# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed import mentions


def test_parse_extracts_bare_handle():
    assert mentions.parse_mentions("ping @christof please") == [("christof", None)]


def test_parse_extracts_handle_with_host():
    assert mentions.parse_mentions("hi @dave@remote.example") == [("dave", "remote.example")]


def test_parse_deduplicates_preserving_order():
    assert mentions.parse_mentions("@a@x.org @b@y.org @a@x.org") == \
        [("a", "x.org"), ("b", "y.org")]


def test_parse_ignores_email_addresses():
    assert mentions.parse_mentions("write to foo@bar.example about it") == []


def test_parse_stops_at_ampersand():
    assert mentions.parse_mentions("@a&b and @c") == [("a", None), ("c", None)]

