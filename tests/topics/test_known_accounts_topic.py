# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.topics.known_accounts_topic import (validate_known_accounts_event,
                                                validate_known_accounts_snapshot_item)


PAYLOAD = {"account_id": 123, "acct": "bob@remote.example", "actor_url": "https://remote/bob"}
VALID   = {"type": "discovered", "payload": PAYLOAD}


def test_valid_event_returns_type_and_payload():
    event_type, payload = validate_known_accounts_event(VALID)

    assert event_type == "discovered"
    assert payload["acct"] == "bob@remote.example"


def test_non_dict_returns_none():
    assert validate_known_accounts_event("x") == (None, None)


def test_missing_type_returns_none():
    event_type, _ = validate_known_accounts_event({"payload": PAYLOAD})

    assert event_type is None


def test_missing_payload_returns_none():
    event_type, _ = validate_known_accounts_event({"type": "discovered"})

    assert event_type is None


def test_non_dict_payload_returns_none():
    event_type, _ = validate_known_accounts_event({"type": "discovered", "payload": "x"})

    assert event_type is None


def test_valid_snapshot_item_returns_item():
    assert validate_known_accounts_snapshot_item(PAYLOAD) == PAYLOAD

def test_non_dict_snapshot_item_returns_none():
    assert validate_known_accounts_snapshot_item("x") is None

