# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
from profed.topics.deliveries_topic import (validate_deliveries_event,
                                            validate_deliveries_snapshot_item)

PAYLOAD = {"attempt":          1,
           "first_attempt_at": "2026-01-01T00:00:00Z"}


def test_valid_delivery_succeeded_returns_payload():
    payload = validate_deliveries_event("delivery_succeeded", PAYLOAD)

    assert payload is not None
    assert payload["attempt"] == 1


def test_valid_delivery_failed_returns_payload():
    assert validate_deliveries_event("delivery_failed", PAYLOAD) is not None


def test_valid_delivery_gave_up_returns_payload():
    assert validate_deliveries_event("delivery_gave_up", PAYLOAD) is not None


def test_old_attempted_event_type_returns_none():
    assert validate_deliveries_event("attempted", PAYLOAD) is None


def test_non_dict_payload_returns_none():
    assert validate_deliveries_event("delivery_succeeded", "x") is None


def test_missing_attempt_returns_none():
    assert validate_deliveries_event("delivery_succeeded", {}) is None


def test_zero_attempt_returns_none():
    bad = {**PAYLOAD, "attempt": 0}

    assert validate_deliveries_event("delivery_succeeded", bad) is None


def test_non_integer_attempt_returns_none():
    bad = {**PAYLOAD, "attempt": "1"}

    assert validate_deliveries_event("delivery_succeeded", bad) is None


def test_valid_snapshot_item_returns_item():
    assert validate_deliveries_snapshot_item(PAYLOAD) == PAYLOAD


def test_invalid_snapshot_item_returns_none():
    assert validate_deliveries_snapshot_item({}) is None

