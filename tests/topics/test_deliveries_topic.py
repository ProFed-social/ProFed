# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
from profed.topics.deliveries_topic import (validate_deliveries_event,
                                            validate_deliveries_snapshot_item)

PAYLOAD = {"attempt":          1,
           "first_attempt_at": "2026-01-01T00:00:00Z"}


def test_valid_done_returns_payload():
    payload = validate_deliveries_event("done", PAYLOAD)

    assert payload is not None
    assert payload["attempt"] == 1


def test_valid_failed_returns_payload():
    assert validate_deliveries_event("failed", PAYLOAD) is not None


def test_valid_gave_up_returns_payload():
    assert validate_deliveries_event("gave_up", PAYLOAD) is not None


def test_valid_attempting_returns_payload():
    assert validate_deliveries_event("attempting", PAYLOAD) is not None


def test_old_attempted_event_type_returns_none():
    assert validate_deliveries_event("attempted", PAYLOAD) is None


def test_non_dict_payload_returns_none():
    assert validate_deliveries_event("done", "x") is None


def test_missing_attempt_returns_none():
    assert validate_deliveries_event("done", {}) is None


def test_zero_attempt_returns_none():
    bad = {**PAYLOAD, "attempt": 0}

    assert validate_deliveries_event("done", bad) is None


def test_non_integer_attempt_returns_none():
    bad = {**PAYLOAD, "attempt": "1"}

    assert validate_deliveries_event("done", bad) is None


def test_valid_snapshot_item_returns_item():
    assert validate_deliveries_snapshot_item(PAYLOAD) == PAYLOAD


def test_invalid_snapshot_item_returns_none():
    assert validate_deliveries_snapshot_item({}) is None


def test_queued_event_accepted():
    assert validate_deliveries_event("queued",
                                     {"username": "alice",
                                      "activity": {"type": "Create"}}) is not None


def test_queued_missing_username_rejected():
    assert validate_deliveries_event("queued", {"activity": {"type": "Create"}}) is None


def test_queued_missing_activity_rejected():
    assert validate_deliveries_event("queued", {"username": "alice"}) is None

