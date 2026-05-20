# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.topics.activities_topic import validate_activities_event, validate_activities_snapshot_item


PAYLOAD = {"username": "alice", "type": "Create", "id": "https://example.com/act/1"}
VALID   = {"type": "Create", "payload": PAYLOAD}


def test_valid_event_returns_type_and_payload():
    event_type, payload = validate_activities_event(VALID)

    assert event_type == "Create"
    assert payload["username"] == "alice"


def test_non_dict_event_returns_none():
    event_type, payload = validate_activities_event("not a dict")

    assert event_type is None
    assert payload    is None


def test_missing_type_returns_none():
    event_type, payload = validate_activities_event({"payload": PAYLOAD})

    assert event_type is None


def test_non_string_type_returns_none():
    event_type, payload = validate_activities_event({"type": 42, "payload": PAYLOAD})

    assert event_type is None


def test_missing_payload_returns_none():
    event_type, payload = validate_activities_event({"type": "Create"})

    assert event_type is None


def test_missing_username_in_payload_returns_none():
    bad = {"type": "Create", "payload": {"type": "Create"}}
    event_type, payload = validate_activities_event(bad)

    assert event_type is None


def test_empty_username_returns_none():
    bad = {"type": "Create", "payload": {"username": "", "type": "Create"}}
    event_type, payload = validate_activities_event(bad)

    assert event_type is None


def test_missing_type_in_payload_returns_none():
    bad = {"type": "Create", "payload": {"username": "alice"}}
    event_type, payload = validate_activities_event(bad)

    assert event_type is None


def test_valid_snapshot_item_returns_item():
    assert validate_activities_snapshot_item(PAYLOAD) == PAYLOAD


def test_invalid_snapshot_item_returns_none():
    assert validate_activities_snapshot_item({"username": "alice"}) is None

