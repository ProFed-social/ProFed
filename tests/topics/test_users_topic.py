# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.topics.users_topic import validate_users_event, validate_users_snapshot_item


PAYLOAD = {"username": "alice"}
VALID   = {"type": "created", "payload": PAYLOAD}


def test_valid_event_returns_type_and_payload():
    event_type, payload = validate_users_event(VALID)

    assert event_type == "created"
    assert payload["username"] == "alice"


def test_non_dict_event_returns_none():
    event_type, payload = validate_users_event("not a dict")

    assert event_type is None
    assert payload    is None


def test_missing_type_returns_none():
    event_type, _ = validate_users_event({"payload": PAYLOAD})

    assert event_type is None


def test_non_string_type_returns_none():
    event_type, _ = validate_users_event({"type": 42, "payload": PAYLOAD})

    assert event_type is None


def test_missing_payload_returns_none():
    event_type, _ = validate_users_event({"type": "created"})

    assert event_type is None


def test_invalid_payload_returns_none():
    event_type, _ = validate_users_event({"type": "created", "payload": {"name": "Alice"}})

    assert event_type is None


def test_valid_snapshot_item_returns_item():
    result = validate_users_snapshot_item(PAYLOAD)

    assert result is not None
    assert result["username"] == "alice"


def test_invalid_snapshot_item_returns_none():
    assert validate_users_snapshot_item({"name": "Alice"}) is None

