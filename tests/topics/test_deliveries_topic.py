# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.topics.deliveries_topic import validate_deliveries_event, validate_deliveries_snapshot_item


PAYLOAD = {"activity_id": "act:1", "recipient": "https://remote/inbox", "success": True, "attempt": 1}
VALID   = {"type": "attempted", "payload": PAYLOAD}


def test_valid_event_returns_type_and_payload():
    event_type, payload = validate_deliveries_event(VALID)

    assert event_type == "attempted"
    assert payload["activity_id"] == "act:1"


def test_non_dict_returns_none():
    assert validate_deliveries_event("x") == (None, None)


def test_unknown_type_returns_none():
    event_type, _ = validate_deliveries_event({"type": "sent", "payload": PAYLOAD})

    assert event_type is None


def test_missing_activity_id_returns_none():
    bad = {"type": "attempted", "payload": {k: v for k, v in PAYLOAD.items() if k != "activity_id"}}
    event_type, _ = validate_deliveries_event(bad)

    assert event_type is None, "expected None for missing activity_id"


def test_missing_recipient_returns_none():
    bad = {"type": "attempted", "payload": {k: v for k, v in PAYLOAD.items() if k != "recipient"}}
    event_type, _ = validate_deliveries_event(bad)

    assert event_type is None, "expected None for missing recipient"


def test_missing_success_returns_none():
    bad = {"type": "attempted", "payload": {k: v for k, v in PAYLOAD.items() if k != "success"}}
    event_type, _ = validate_deliveries_event(bad)

    assert event_type is None, "expected None for missing success"


def test_missing_attempt_returns_none():
    bad = {"type": "attempted", "payload": {k: v for k, v in PAYLOAD.items() if k != "attempt"}}
    event_type, _ = validate_deliveries_event(bad)

    assert event_type is None, "expected None for missing attempt"



def test_non_integer_attempt_returns_none():
    bad = {"type": "attempted", "payload": {**PAYLOAD, "attempt": "1"}}
    event_type, _ = validate_deliveries_event(bad)

    assert event_type is None


def test_zero_attempt_returns_none():
    bad = {"type": "attempted", "payload": {**PAYLOAD, "attempt": 0}}
    event_type, _ = validate_deliveries_event(bad)

    assert event_type is None


def test_valid_snapshot_item_returns_item():
    assert validate_deliveries_snapshot_item(PAYLOAD) == PAYLOAD


def test_invalid_snapshot_item_returns_none():
    assert validate_deliveries_snapshot_item({"activity_id": "x"}) is None

