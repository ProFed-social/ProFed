# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.topics.oauth_apps_topic import (validate_oauth_apps_event,
                                            validate_oauth_apps_snapshot_item)


PAYLOAD = {"client_secret": "sec456",
           "client_name":   "TestApp",
           "redirect_uris": "https://example.com/callback",
           "scopes":        "read write"}


def test_valid_created_event_returns_payload():
    payload = validate_oauth_apps_event("created", PAYLOAD)

    assert payload is not None
    assert payload["client_name"] == "TestApp"


def test_unknown_event_type_returns_none():
    assert validate_oauth_apps_event("updated", PAYLOAD) is None


def test_non_dict_payload_returns_none():
    assert validate_oauth_apps_event("created", "x") is None


def test_missing_client_secret_returns_none():
    bad = {k: v for k, v in PAYLOAD.items() if k != "client_secret"}

    assert validate_oauth_apps_event("created", bad) is None


def test_missing_client_name_returns_none():
    bad = {k: v for k, v in PAYLOAD.items() if k != "client_name"}

    assert validate_oauth_apps_event("created", bad) is None


def test_missing_redirect_uris_returns_none():
    bad = {k: v for k, v in PAYLOAD.items() if k != "redirect_uris"}

    assert validate_oauth_apps_event("created", bad) is None


def test_missing_scopes_returns_none():
    bad = {k: v for k, v in PAYLOAD.items() if k != "scopes"}

    assert validate_oauth_apps_event("created", bad) is None


def test_empty_field_returns_none():
    bad = {**PAYLOAD, "client_secret": ""}

    assert validate_oauth_apps_event("created", bad) is None


def test_valid_snapshot_item_returns_item():
    item = {"client_id": "id123", **PAYLOAD}

    assert validate_oauth_apps_snapshot_item(item) == item


def test_snapshot_item_missing_field_returns_none():
    assert validate_oauth_apps_snapshot_item({"client_id": "id123"}) is None

