# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.topics.unknown_actors_topic import (throttled_id,
                                                validate_unknown_actors_event,
                                                validate_unknown_actors_snapshot_item)


def test_an_discovered_acct_event_passes():
    assert validate_unknown_actors_event("discovered_acct", {}) == {}


def test_a_discovered_url_event_passes():
    assert validate_unknown_actors_event("discovered_url", {}) == {}


def test_an_unknown_event_type_is_rejected():
    assert validate_unknown_actors_event("discovered", {}) is None


def test_a_payload_that_is_no_dict_is_rejected():
    assert validate_unknown_actors_event("discovered_url", "nope") is None


def test_a_snapshot_item_that_is_no_dict_is_rejected():
    assert validate_unknown_actors_snapshot_item([]) is None


def test_a_snapshot_item_passes():
    assert validate_unknown_actors_snapshot_item({"a": 1}) == {"a": 1}


def test_the_throttled_id_is_stable_within_a_window():
    assert throttled_id("inbox", "https://a.test/x", 100000) == throttled_id("inbox", "https://a.test/x", 100000)


def test_the_throttled_id_separates_the_names():
    assert throttled_id("inbox", "https://a.test/x", 100000) != throttled_id("inbox", "https://a.test/y", 100000)


def test_the_throttled_id_separates_the_sources():
    assert throttled_id("inbox", "https://a.test/x", 100000) != \
           throttled_id("known_accounts", "https://a.test/x", 100000)


def test_the_throttled_id_changes_with_the_window():
    assert throttled_id("inbox", "https://a.test/x", 1) != throttled_id("inbox", "https://a.test/x", 100000)

