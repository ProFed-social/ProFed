# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.topics.followers_topic import validate_followers_event, validate_followers_snapshot_item


PAYLOAD = {"follower": "alice@a.example", "following": "bob@b.example"}


def test_valid_created_event_returns_type_and_payload():
    event_type, payload = validate_followers_event({"type": "created", "payload": PAYLOAD})

    assert event_type == "created"
    assert payload["follower"] == "alice@a.example"


def test_valid_deleted_event_returns_type_and_payload():
    event_type, payload = validate_followers_event({"type": "deleted", "payload": PAYLOAD})

    assert event_type == "deleted"


def test_non_dict_returns_none():
    assert validate_followers_event("x") == (None, None)


def test_unknown_type_returns_none():
    event_type, _ = validate_followers_event({"type": "updated", "payload": PAYLOAD})

    assert event_type is None


def test_missing_follower_returns_none():
    bad = {"type": "created", "payload": {"following": "bob@b.example"}}
    event_type, _ = validate_followers_event(bad)

    assert event_type is None


def test_empty_following_returns_none():
    bad = {"type": "created", "payload": {"follower": "alice@a.example", "following": ""}}
    event_type, _ = validate_followers_event(bad)

    assert event_type is None


def test_valid_snapshot_item_returns_item():
    assert validate_followers_snapshot_item(PAYLOAD) == PAYLOAD


def test_invalid_snapshot_item_returns_none():
    assert validate_followers_snapshot_item({"follower": "alice@a.example"}) is None

