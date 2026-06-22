# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.topics.preferences_topic import (validate_preferences_event,
                                             validate_preferences_snapshot_item)

PAYLOAD = {"privacy": "private",
           "sensitive": True,
           "language": "de"}


def test_valid_updated_returns_payload():
    payload = validate_preferences_event("updated", PAYLOAD)

    assert payload is not None
    assert payload["privacy"] == "private"
    assert payload["sensitive"] is True
    assert payload["language"] == "de"


def test_partial_updated_returns_payload():
    assert validate_preferences_event("updated", {"privacy": "public"}) is not None


def test_null_language_is_allowed():
    assert validate_preferences_event("updated", {"language": None}) is not None


def test_unknown_event_type_returns_none():
    assert validate_preferences_event("created", PAYLOAD) is None


def test_non_dict_payload_returns_none():
    assert validate_preferences_event("updated", "x") is None


def test_empty_payload_returns_none():
    assert validate_preferences_event("updated", {}) is None


def test_invalid_privacy_returns_none():
    assert validate_preferences_event("updated", {"privacy": "secret"}) is None


def test_non_bool_sensitive_returns_none():
    assert validate_preferences_event("updated", {"sensitive": "yes"}) is None


def test_non_string_language_returns_none():
    assert validate_preferences_event("updated", {"language": 7}) is None


def test_unknown_field_returns_none():
    assert validate_preferences_event("updated", {"theme": "dark"}) is None


SNAPSHOT = {"username": "alice",
            "privacy": "private",
            "sensitive": True,
            "language": "de"}


def test_valid_snapshot_item_returns_item():
    assert validate_preferences_snapshot_item(SNAPSHOT) == SNAPSHOT


def test_snapshot_item_with_only_username_is_allowed():
    assert validate_preferences_snapshot_item({"username": "alice"}) == {"username": "alice"}


def test_snapshot_item_missing_username_returns_none():
    assert validate_preferences_snapshot_item(PAYLOAD) is None


def test_snapshot_item_with_invalid_pref_returns_none():
    assert validate_preferences_snapshot_item({"username": "alice",
                                               "privacy": "secret"}) is None


def test_empty_snapshot_item_returns_none():
    assert validate_preferences_snapshot_item({}) is None

