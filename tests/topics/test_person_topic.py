# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.topics.person_topic import (validate_person_event,
                                        validate_person_snapshot_item)


PAYLOAD = {"preferredUsername": "alice",
           "id": "https://example.com/actors/alice",
           "type": "Person"}


def test_created_with_valid_username_returns_payload():
    assert validate_person_event("created", PAYLOAD) == PAYLOAD


def test_updated_with_valid_username_returns_payload():
    assert validate_person_event("updated", PAYLOAD) == PAYLOAD


def test_created_without_username_returns_none():
    assert validate_person_event("created", {"id": "https://example.com/actors/alice"}) is None


def test_created_with_empty_username_returns_none():
    assert validate_person_event("created", {"preferredUsername": ""}) is None


def test_non_dict_payload_returns_none():
    assert validate_person_event("created", "x") is None


def test_deleted_with_empty_payload_returns_empty():
    assert validate_person_event("deleted", {}) == {}


def test_deleted_with_non_empty_payload_returns_none():
    assert validate_person_event("deleted", PAYLOAD) is None


def test_unknown_event_type_returns_none():
    assert validate_person_event("exploded", PAYLOAD) is None


def test_valid_snapshot_item_returns_item():
    assert validate_person_snapshot_item(PAYLOAD) == PAYLOAD


def test_snapshot_item_without_username_returns_none():
    assert validate_person_snapshot_item({"id": "https://example.com/actors/alice"}) is None


def test_non_dict_snapshot_item_returns_none():
    assert validate_person_snapshot_item("x") is None

