# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.topics.oauth_codes_topic import validate_oauth_codes_event, validate_oauth_codes_snapshot_item


ISSUED   = {"code":       "abc",
            "client_id": "id123",
            "username":  "alice",
            "id_token":  "tok",
            "expires_at": "2026-12-31T00:00:00Z"}
CONSUMED = {"code": "abc"}


def test_valid_issued_event_returns_type_and_payload():
    event_type, payload = validate_oauth_codes_event({"type": "issued", "payload": ISSUED})

    assert event_type == "issued"
    assert payload["code"] == "abc"


def test_valid_consumed_event_returns_type_and_payload():
    event_type, payload = validate_oauth_codes_event({"type": "consumed", "payload": CONSUMED})

    assert event_type == "consumed"
    assert payload["code"] == "abc"


def test_non_dict_returns_none():
    assert validate_oauth_codes_event("x") == (None, None)


def test_unknown_type_returns_none():
    event_type, _ = validate_oauth_codes_event({"type": "deleted", "payload": ISSUED})

    assert event_type is None


def test_missing_code_returns_none():
    bad = {"type": "issued", "payload": {k: v for k, v in ISSUED.items() if k != "code"}}
    event_type, _ = validate_oauth_codes_event(bad)

    assert event_type is None, "expected None for missing code"


def test_missing_client_id_returns_none():
    bad = {"type": "issued", "payload": {k: v for k, v in ISSUED.items() if k != "client_id"}}
    event_type, _ = validate_oauth_codes_event(bad)

    assert event_type is None, "expected None for missing client_id"


def test_missing_username_returns_none():
    bad = {"type": "issued", "payload": {k: v for k, v in ISSUED.items() if k != "username"}}
    event_type, _ = validate_oauth_codes_event(bad)

    assert event_type is None, "expected None for missing username"


def test_missing_id_token_returns_none():
    bad = {"type": "issued", "payload": {k: v for k, v in ISSUED.items() if k != "id_token"}}
    event_type, _ = validate_oauth_codes_event(bad)

    assert event_type is None, "expected None for missing id_token"


def test_missing_expires_at_returns_none():
    bad = {"type": "issued", "payload": {k: v for k, v in ISSUED.items() if k != "expires_at"}}
    event_type, _ = validate_oauth_codes_event(bad)

    assert event_type is None, "expected None for missing expires_at"


def test_missing_code_in_consumed_returns_none():
    event_type, _ = validate_oauth_codes_event({"type": "consumed", "payload": {}})

    assert event_type is None


def test_valid_snapshot_item_returns_item():
    assert validate_oauth_codes_snapshot_item(ISSUED) == ISSUED


def test_invalid_snapshot_item_returns_none():
    assert validate_oauth_codes_snapshot_item({"code": "abc"}) is None

