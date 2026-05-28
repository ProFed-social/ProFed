# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.topics.oauth_codes_topic import (validate_oauth_codes_event,
                                             validate_oauth_codes_snapshot_item)


ISSUED = {"client_id":  "id123",
          "username":   "alice",
          "id_token":   "tok",
          "expires_at": "2026-12-31T00:00:00Z"}


def test_valid_issued_event_returns_payload():
    payload = validate_oauth_codes_event("issued", ISSUED)

    assert payload is not None
    assert payload["client_id"] == "id123"


def test_valid_consumed_event_returns_empty_payload():
    assert validate_oauth_codes_event("consumed", {}) == {}


def test_unknown_event_type_returns_none():
    assert validate_oauth_codes_event("deleted", ISSUED) is None


def test_non_dict_payload_returns_none():
    assert validate_oauth_codes_event("issued", "x") is None


def test_issued_missing_client_id_returns_none():
    bad = {k: v for k, v in ISSUED.items() if k != "client_id"}

    assert validate_oauth_codes_event("issued", bad) is None


def test_issued_missing_username_returns_none():
    bad = {k: v for k, v in ISSUED.items() if k != "username"}

    assert validate_oauth_codes_event("issued", bad) is None


def test_issued_missing_id_token_returns_none():
    bad = {k: v for k, v in ISSUED.items() if k != "id_token"}

    assert validate_oauth_codes_event("issued", bad) is None


def test_issued_missing_expires_at_returns_none():
    bad = {k: v for k, v in ISSUED.items() if k != "expires_at"}

    assert validate_oauth_codes_event("issued", bad) is None


def test_consumed_with_non_empty_payload_returns_none():
    assert validate_oauth_codes_event("consumed", {"client_id": "x"}) is None


def test_valid_snapshot_item_returns_item():
    assert validate_oauth_codes_snapshot_item(ISSUED) == ISSUED


def test_invalid_snapshot_item_returns_none():
    assert validate_oauth_codes_snapshot_item({}) is None

