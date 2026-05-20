# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.topics.incoming_activities_topic import (validate_incoming_activities_event,
                                                     validate_incoming_activities_snapshot_item)


PAYLOAD = {"username": "alice", "activity": {"type": "Follow", "actor": "https://remote/bob"}}
VALID   = {"type": "Follow", "payload": PAYLOAD}


def test_valid_event_returns_type_and_payload():
    event_type, payload = validate_incoming_activities_event(VALID)

    assert event_type == "Follow"
    assert payload["username"] == "alice"


def test_non_dict_returns_none():
    assert validate_incoming_activities_event("x") == (None, None)


def test_missing_type_returns_none():
    event_type, _ = validate_incoming_activities_event({"payload": PAYLOAD})

    assert event_type is None


def test_empty_type_returns_none():
    event_type, _ = validate_incoming_activities_event({"type": "", "payload": PAYLOAD})

    assert event_type is None


def test_missing_payload_returns_none():
    event_type, _ = validate_incoming_activities_event({"type": "Follow"})

    assert event_type is None


def test_missing_username_in_payload_returns_none():
    bad = {"type": "Follow", "payload": {"activity": {}}}
    event_type, _ = validate_incoming_activities_event(bad)

    assert event_type is None


def test_missing_activity_in_payload_returns_none():
    bad = {"type": "Follow", "payload": {"username": "alice"}}
    event_type, _ = validate_incoming_activities_event(bad)

    assert event_type is None


def test_snapshot_item_is_not_supported():
    assert validate_incoming_activities_snapshot_item({"username": "alice"}) is None


def test_snapshot_item_handles_none_input():
    assert validate_incoming_activities_snapshot_item(None) is None

