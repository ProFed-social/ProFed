# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.topics.resolution_topic import (validate_resolution_event,
                                            validate_resolution_snapshot_item)


def test_attempting_needs_no_version():
    payload = validate_resolution_event("attempting", {"object_id": "https://remote/notes/1", "attempt": 2})

    assert payload is not None
    assert payload["object_id"] == "https://remote/notes/1"
    assert payload["attempt"] == 2


def test_succeeded_carries_a_version():
    payload = validate_resolution_event("succeeded", {"object_id": "https://remote/notes/1",
                                                      "version": "2026-01-01T00:00:00Z"})

    assert payload["version"] == "2026-01-01T00:00:00Z"


def test_failed_returns_payload():
    assert validate_resolution_event("failed", {"object_id": "https://remote/notes/1"}) is not None


def test_not_found_carries_its_count():
    payload = validate_resolution_event("not_found", {"object_id": "https://remote/notes/1", "not_found_count": 3})

    assert payload["not_found_count"] == 3


def test_tombstone_carries_a_future_version():
    payload = validate_resolution_event("tombstone", {"object_id": "https://remote/notes/1",
                                                      "version": "2026-01-05T00:00:00Z"})

    assert payload is not None
    assert payload["version"] == "2026-01-05T00:00:00Z"


def test_counts_default_to_zero():
    payload = validate_resolution_event("attempting", {"object_id": "https://remote/notes/1"})

    assert payload["attempt"] == 0
    assert payload["not_found_count"] == 0


def test_not_found_keeps_tombstone_extra():
    payload = validate_resolution_event("not_found", {"object_id": "https://remote/notes/1", "status": 404})

    assert payload["status"] == 404


def test_unknown_event_type_returns_none():
    assert validate_resolution_event("deleted", {"object_id": "https://remote/notes/1"}) is None


def test_missing_object_id_returns_none():
    assert validate_resolution_event("succeeded", {"version": "2026-01-01T00:00:00Z"}) is None


def test_empty_object_id_returns_none():
    assert validate_resolution_event("attempting", {"object_id": ""}) is None


def test_non_dict_payload_returns_none():
    assert validate_resolution_event("attempting", "nope") is None


def test_snapshot_item_valid_returns_payload():
    assert validate_resolution_snapshot_item({"object_id": "https://remote/notes/1"}) is not None


def test_snapshot_item_invalid_returns_none():
    assert validate_resolution_snapshot_item({"version": "2026-01-01T00:00:00Z"}) is None

