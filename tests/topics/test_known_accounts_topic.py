# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.topics.known_accounts_topic import (validate_known_accounts_event,
                                                validate_known_accounts_snapshot_item)


PAYLOAD = {"acct":      "bob@remote.example",
           "actor_url": "https://remote/bob"}


def test_valid_discovered_event_returns_payload():
    payload = validate_known_accounts_event("discovered", PAYLOAD)

    assert payload is not None
    assert payload["acct"] == "bob@remote.example"


def test_valid_follow_accepted_event_returns_payload():
    assert validate_known_accounts_event("follow_accepted", PAYLOAD) is not None


def test_unknown_event_type_returns_none():
    assert validate_known_accounts_event("renamed", PAYLOAD) is None


def test_non_dict_payload_returns_none():
    assert validate_known_accounts_event("discovered", "x") is None


def test_valid_snapshot_item_returns_item():
    assert validate_known_accounts_snapshot_item(PAYLOAD) == PAYLOAD


def test_non_dict_snapshot_item_returns_none():
    assert validate_known_accounts_snapshot_item("x") is None

