# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.topics.unknown_actors_topic import (validate_unknown_actors_event,
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

