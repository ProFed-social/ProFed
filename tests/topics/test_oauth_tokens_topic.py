# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.topics.oauth_tokens_topic import validate_oauth_tokens_event, validate_oauth_tokens_snapshot_item


ISSUED  = {"token": "tok123", "username": "alice", "client_id": "id123"}
REVOKED = {"token": "tok123"}


def test_valid_issued_event_returns_type_and_payload():
    event_type, payload = validate_oauth_tokens_event({"type": "issued", "payload": ISSUED})

    assert event_type == "issued"
    assert payload["token"] == "tok123"


def test_valid_revoked_event_returns_type_and_payload():
    event_type, payload = validate_oauth_tokens_event({"type": "revoked", "payload": REVOKED})

    assert event_type == "revoked"
    assert payload["token"] == "tok123"


def test_non_dict_returns_none():
    assert validate_oauth_tokens_event("x") == (None, None)


def test_unknown_type_returns_none():
    event_type, _ = validate_oauth_tokens_event({"type": "deleted", "payload": ISSUED})

    assert event_type is None


def test_missing_token_returns_none():
    bad = {"type": "issued", "payload": {k: v for k, v in ISSUED.items() if k != "token"}}
    event_type, _ = validate_oauth_tokens_event(bad)

    assert event_type is None, "expected None for missing token"


def test_missing_username_returns_none():
    bad = {"type": "issued", "payload": {k: v for k, v in ISSUED.items() if k != "username"}}
    event_type, _ = validate_oauth_tokens_event(bad)

    assert event_type is None, "expected None for missing username"


def test_missing_client_id_returns_none():
    bad = {"type": "issued", "payload": {k: v for k, v in ISSUED.items() if k != "client_id"}}
    event_type, _ = validate_oauth_tokens_event(bad)

    assert event_type is None, "expected None for missing client_id"


def test_empty_token_in_revoked_returns_none():
    event_type, _ = validate_oauth_tokens_event({"type": "revoked", "payload": {"token": ""}})

    assert event_type is None


def test_missing_token_in_revoked_returns_none():
    event_type, _ = validate_oauth_tokens_event({"type": "revoked", "payload": {}})

    assert event_type is None


def test_valid_snapshot_item_returns_item():
    assert validate_oauth_tokens_snapshot_item(ISSUED) == ISSUED


def test_invalid_snapshot_item_returns_none():
    assert validate_oauth_tokens_snapshot_item({"token": "x"}) is None

