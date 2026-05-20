# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.topics.media_topic import validate_media_event, validate_media_snapshot_item


UPLOADED = {"type":    "uploaded",
            "payload": {"file_id":      "abc123",
                        "url":          "https://example.com/media/ab/abc123",
                        "content_type": "image/jpeg",
                        "size":          45678,
                        "uploader":     "alice@example.com"}}


DELETED = {"type":    "deleted",
           "payload": {"file_id": "abc123"}}


def test_valid_uploaded_event_returns_type_and_payload():
    event_type, payload = validate_media_event(UPLOADED)

    assert event_type          == "uploaded"
    assert payload["file_id"]  == "abc123"
    assert payload["size"]     == 45678
    assert payload["uploader"] == "alice@example.com"


def test_valid_deleted_event_returns_type_and_payload():
    event_type, payload = validate_media_event(DELETED)

    assert event_type         == "deleted"
    assert payload["file_id"] == "abc123"


def test_missing_required_field_in_uploaded_returns_none():
    event = {"type":    "uploaded",
             "payload": {"file_id": "abc123",
                         "url":     "https://example.com/media/ab/abc123"}}
    event_type, payload = validate_media_event(event)

    assert event_type is None
    assert payload    is None


def test_non_integer_size_in_uploaded_returns_none():
    event = {**UPLOADED,
             "payload": {**UPLOADED["payload"], "size": "45678"}}
    event_type, payload = validate_media_event(event)

    assert event_type is None


def test_missing_file_id_in_deleted_returns_none():
    event_type, payload = validate_media_event({"type": "deleted", "payload": {}})

    assert event_type is None


def test_unknown_event_type_returns_none():
    event_type, payload = validate_media_event({"type": "processed", "payload": {}})

    assert event_type is None


def test_non_dict_event_returns_none():
    event_type, payload = validate_media_event("not a dict")

    assert event_type is None
    assert payload    is None


def test_valid_snapshot_item_returns_item():
    item = {"file_id": "abc123", "url": "https://example.com/media/ab/abc123"}

    assert validate_media_snapshot_item(item) == item


def test_snapshot_item_without_file_id_returns_none():
    assert validate_media_snapshot_item({"url": "https://example.com"}) is None

