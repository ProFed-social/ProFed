# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.topics.media_topic import (validate_media_event,
                                       validate_media_snapshot_item)


UPLOADED = {"url": "https://example.com/media/ab/abc123",
            "content_type": "image/jpeg",
            "size": 45678,
            "uploader": "alice@example.com"}


def test_valid_uploaded_event_returns_payload():
    payload = validate_media_event("uploaded", UPLOADED)

    assert payload is not None
    assert payload["size"] == 45678
    assert payload["uploader"] == "alice@example.com"


def test_valid_deleted_event_returns_empty_payload():
    assert validate_media_event("deleted", {}) == {}


def test_valid_variants_added_event_returns_payload():
    variants = {"small": {"url": "https://example.com/media/ab/abc123_small",
                          "width": 80,
                          "height": 80,
                          "content_type": "image/jpeg"}}

    assert validate_media_event("variants_added", variants) == variants


def test_uploaded_missing_required_field_returns_none():
    bad = {k: v for k, v in UPLOADED.items() if k != "size"}

    assert validate_media_event("uploaded", bad) is None


def test_uploaded_non_integer_size_returns_none():
    bad = {**UPLOADED, "size": "45678"}

    assert validate_media_event("uploaded", bad) is None


def test_deleted_with_non_empty_payload_returns_none():
    assert validate_media_event("deleted", {"file_id": "x"}) is None


def test_variants_added_missing_field_in_variant_returns_none():
    bad = {"small": {"url": "u", "width": 80}}

    assert validate_media_event("variants_added", bad) is None


def test_variants_added_non_dict_variant_returns_none():
    bad = {"small": "not a dict"}

    assert validate_media_event("variants_added", bad) is None


def test_unknown_event_type_returns_none():
    assert validate_media_event("processed", {}) is None


def test_non_dict_payload_returns_none():
    assert validate_media_event("uploaded", "not a dict") is None


def test_valid_snapshot_item_returns_item():
    item = {"file_id": "abc123", "url": "https://example.com"}

    assert validate_media_snapshot_item(item) == item


def test_snapshot_item_without_file_id_returns_none():
    assert validate_media_snapshot_item({"url": "x"}) is None


def test_uploaded_c2s_shape_with_preview_passes():
    c2s = {**UPLOADED,
           "preview_url": "https://example.com/media/ab/abc123_small",
           "width": 1200,
           "height": 800,
           "preview_width": 400,
           "preview_height": 267}

    result = validate_media_event("uploaded", c2s)

    assert result is not None
    assert result["width"] == 1200
    assert result["preview_url"] == "https://example.com/media/ab/abc123_small"
    assert result["preview_height"] == 267

