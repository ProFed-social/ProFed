# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.topics.oauth_apps_topic import validate_oauth_apps_event, validate_oauth_apps_snapshot_item


PAYLOAD = {"client_id":     "id123",
           "client_secret": "sec456",
           "client_name":   "TestApp",
           "redirect_uris": "https://example.com/callback",
           "scopes":        "read write"}
VALID   = {"type": "created", "payload": PAYLOAD}


def test_valid_event_returns_type_and_payload():
    event_type, payload = validate_oauth_apps_event(VALID)

    assert event_type == "created"
    assert payload["client_name"] == "TestApp"


def test_non_dict_returns_none():
    assert validate_oauth_apps_event("x") == (None, None)


def test_unknown_type_returns_none():
    event_type, _ = validate_oauth_apps_event({"type": "updated", "payload": PAYLOAD})

    assert event_type is None


def test_missing_client_id_returns_none():
    bad = {"type": "created", "payload": {k: v for k, v in PAYLOAD.items() if k != "client_id"}}
    event_type, _ = validate_oauth_apps_event(bad)

    assert event_type is None, "expected None for missing client_id"


def test_missing_client_secret_returns_none():
    bad = {"type": "created", "payload": {k: v for k, v in PAYLOAD.items() if k != "client_secret"}}
    event_type, _ = validate_oauth_apps_event(bad)

    assert event_type is None, "expected None for missing client_secret"


def test_missing_client_name_returns_none():
    bad = {"type": "created", "payload": {k: v for k, v in PAYLOAD.items() if k != "client_name"}}
    event_type, _ = validate_oauth_apps_event(bad)

    assert event_type is None, "expected None for missing client_name"


def test_missing_redirect_uris_returns_none():
    bad = {"type": "created", "payload": {k: v for k, v in PAYLOAD.items() if k != "redirect_uris"}}
    event_type, _ = validate_oauth_apps_event(bad)

    assert event_type is None, "expected None for missing redirect_uris"


def test_missing_scopes_returns_none():
    bad = {"type": "created", "payload": {k: v for k, v in PAYLOAD.items() if k != "scopes"}}
    event_type, _ = validate_oauth_apps_event(bad)

    assert event_type is None, "expected None for missing scopes"


def test_empty_field_returns_none():
    bad = {"type": "created", "payload": {**PAYLOAD, "client_id": ""}}
    event_type, _ = validate_oauth_apps_event(bad)

    assert event_type is None


def test_valid_snapshot_item_returns_item():
    assert validate_oauth_apps_snapshot_item(PAYLOAD) == PAYLOAD


def test_invalid_snapshot_item_returns_none():
    assert validate_oauth_apps_snapshot_item({"client_id": "x"}) is None
