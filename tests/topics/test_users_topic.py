# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.topics.users_topic import (validate_users_event,
                                       validate_users_snapshot_item)


def test_created_with_full_payload_passes_through():
    payload = {"name": "Alice",
               "summary": "Engineer",
               "resume": {"experience": []},
               "avatar_url": "https://example.com/a.png",
               "header_url": "https://example.com/h.jpg",
               "public_key_pem": "PUB",
               "private_key_pem": "PRIV"}

    result = validate_users_event("created", payload)

    assert result is not None
    assert result["name"] == "Alice"
    assert result["public_key_pem"] == "PUB"
    assert result["private_key_pem"] == "PRIV"


def test_created_with_empty_payload_is_valid():
    assert validate_users_event("created", {}) == {}


def test_created_with_unknown_field_returns_none():
    assert validate_users_event("created", {"foo": "bar"}) is None


def test_created_with_invalid_resume_returns_none():
    assert validate_users_event("created", {"resume": {"experience": "not a list"}}) is None


def test_deleted_with_empty_payload_is_valid():
    assert validate_users_event("deleted", {}) == {}


def test_deleted_with_non_empty_payload_returns_none():
    assert validate_users_event("deleted", {"name": "x"}) is None


def test_profile_edited_with_text_fields():
    assert validate_users_event("profile_edited",
                                {"name": "Alice", "summary": "Hi"}) == {"name": "Alice", "summary": "Hi"}


def test_profile_edited_with_null_value_keeps_null():
    assert validate_users_event("profile_edited", {"summary": None}) == {"summary": None}


def test_profile_edited_empty_payload_returns_none():
    assert validate_users_event("profile_edited", {}) is None


def test_profile_edited_unknown_field_returns_none():
    assert validate_users_event("profile_edited", {"name": "x", "foo": "bar"}) is None


def test_profile_edited_invalid_type_returns_none():
    assert validate_users_event("profile_edited", {"locked": "not a bool"}) is None


def test_avatar_changed_with_url():
    assert validate_users_event("avatar_changed",
                                {"url": "https://x/a.png"}) == {"url": "https://x/a.png"}


def test_avatar_changed_empty_is_clear():
    assert validate_users_event("avatar_changed", {}) == {}


def test_avatar_changed_invalid_url_returns_none():
    assert validate_users_event("avatar_changed", {"url": 42}) is None


def test_avatar_changed_extra_field_returns_none():
    assert validate_users_event("avatar_changed", {"url": "x", "foo": "y"}) is None


def test_header_changed_with_url():
    assert validate_users_event("header_changed",
                                {"url": "https://x/h.jpg"}) == {"url": "https://x/h.jpg"}


def test_header_changed_empty_is_clear():
    assert validate_users_event("header_changed", {}) == {}


def test_cv_changed_with_resume():
    result = validate_users_event("cv_changed", {"resume": {"experience": []}})

    assert result is not None
    assert "resume" in result


def test_cv_changed_empty_is_clear():
    assert validate_users_event("cv_changed", {}) == {}


def test_cv_changed_with_null_resume_is_clear():
    assert validate_users_event("cv_changed", {"resume": None}) == {}


def test_cv_changed_with_invalid_resume_returns_none():
    assert validate_users_event("cv_changed", {"resume": {"experience": "bad"}}) is None


def test_keys_generated_valid():
    assert validate_users_event("keys_generated",
                                {"public_key_pem": "PUB",
                                 "private_key_pem": "PRIV"}) == {"public_key_pem": "PUB",
                                                                 "private_key_pem": "PRIV"}


def test_keys_generated_missing_key_returns_none():
    assert validate_users_event("keys_generated", {"public_key_pem": "PUB"}) is None


def test_keys_generated_empty_string_returns_none():
    assert validate_users_event("keys_generated",
                                {"public_key_pem": "", "private_key_pem": "PRIV"}) is None


def test_unknown_event_type_returns_none():
    assert validate_users_event("renamed", {}) is None


def test_non_dict_payload_returns_none():
    assert validate_users_event("created", "not a dict") is None


def test_valid_snapshot_item_returns_item():
    result = validate_users_snapshot_item({"username": "alice"})

    assert result is not None
    assert result["username"] == "alice"


def test_snapshot_item_missing_username_returns_none():
    assert validate_users_snapshot_item({"name": "Alice"}) is None


def test_non_dict_snapshot_item_returns_none():
    assert validate_users_snapshot_item("not a dict") is None
