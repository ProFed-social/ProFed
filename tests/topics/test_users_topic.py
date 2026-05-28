# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.topics.users_topic import (validate_users_event,
                                       validate_users_snapshot_item)


def test_valid_created_event_returns_payload_without_username():
    payload = validate_users_event("created", {"name": "Alice"})

    assert payload is not None
    assert payload.get("name") == "Alice"
    assert "username" not in payload

def test_valid_updated_event_returns_payload():
    payload = validate_users_event("updated", {"summary": "hello"})

    assert payload is not None
    assert payload.get("summary") == "hello"


def test_valid_deleted_event_returns_empty_payload():
    assert validate_users_event("deleted", {}) == {}


def test_unknown_event_type_returns_none():
    assert validate_users_event("renamed", {}) is None


def test_non_dict_payload_returns_none():
    assert validate_users_event("created", "not a dict") is None


def test_deleted_with_non_empty_payload_returns_none():
    assert validate_users_event("deleted", {"name": "x"}) is None


def test_valid_snapshot_item_returns_item():
    result = validate_users_snapshot_item({"username": "alice"})

    assert result is not None
    assert result["username"] == "alice"


def test_snapshot_item_missing_username_returns_none():
    assert validate_users_snapshot_item({"name": "Alice"}) is None


def test_non_dict_snapshot_item_returns_none():
    assert validate_users_snapshot_item("not a dict") is None

