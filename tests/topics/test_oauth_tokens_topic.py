# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.topics.oauth_tokens_topic import (validate_oauth_tokens_event,
                                              validate_oauth_tokens_snapshot_item)


ISSUED = {"username":  "alice",
          "client_id": "id123"}


def test_valid_issued_event_returns_payload():
    payload = validate_oauth_tokens_event("issued", ISSUED)

    assert payload is not None
    assert payload["username"] == "alice"


def test_valid_revoked_event_returns_empty_payload():
    assert validate_oauth_tokens_event("revoked", {}) == {}


def test_unknown_event_type_returns_none():
    assert validate_oauth_tokens_event("deleted", ISSUED) is None


def test_non_dict_payload_returns_none():
    assert validate_oauth_tokens_event("issued", "x") is None


def test_issued_missing_username_returns_none():
    assert validate_oauth_tokens_event("issued", {"client_id": "id123"}) is None


def test_issued_missing_client_id_returns_none():
    assert validate_oauth_tokens_event("issued", {"username": "alice"}) is None


def test_revoked_with_non_empty_payload_returns_none():
    assert validate_oauth_tokens_event("revoked", {"username": "x"}) is None


def test_valid_snapshot_item_returns_item():
    assert validate_oauth_tokens_snapshot_item(ISSUED) == ISSUED


def test_invalid_snapshot_item_returns_none():
    assert validate_oauth_tokens_snapshot_item({}) is None

