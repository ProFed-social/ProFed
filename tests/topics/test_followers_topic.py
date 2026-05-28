# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.topics.followers_topic import (validate_followers_event,
                                           validate_followers_snapshot_item)


def test_valid_created_event_returns_empty_payload():
    assert validate_followers_event("created", {}) == {}


def test_valid_deleted_event_returns_empty_payload():
    assert validate_followers_event("deleted", {}) == {}


def test_unknown_event_type_returns_none():
    assert validate_followers_event("updated", {}) is None


def test_non_dict_payload_returns_none():
    assert validate_followers_event("created", "x") is None


def test_valid_snapshot_item_returns_item():
    item = {"follower": "alice@a.example", "following": "bob@b.example"}

    assert validate_followers_snapshot_item(item) == item


def test_snapshot_item_missing_follower_returns_none():
    bad = {"following": "bob@b.example"}

    assert validate_followers_snapshot_item(bad) is None


def test_snapshot_item_missing_following_returns_none():
    bad = {"follower": "alice@a.example"}

    assert validate_followers_snapshot_item(bad) is None


def test_non_dict_snapshot_item_returns_none():
    assert validate_followers_snapshot_item("x") is None

