# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.topics.remote_actors_topic import (validate_remote_actors_event,
                                               validate_remote_actors_snapshot_item)


PAYLOAD = {"acct": "bob@remote.example",
           "actor_url": "https://remote.example/users/bob",
           "actor_data": {"type": "Person", "publicKey": {"publicKeyPem": "X"}}}


def test_valid_discovered_event_returns_payload():
    payload = validate_remote_actors_event("discovered", PAYLOAD)

    assert payload is not None
    assert payload["actor_url"] == "https://remote.example/users/bob"


def test_non_discovered_event_is_rejected():
    assert validate_remote_actors_event("created", PAYLOAD) is None


def test_unknown_event_type_returns_none():
    assert validate_remote_actors_event("renamed", PAYLOAD) is None


def test_non_dict_payload_returns_none():
    assert validate_remote_actors_event("discovered", "x") is None


def test_valid_snapshot_item_returns_item():
    assert validate_remote_actors_snapshot_item(PAYLOAD) == PAYLOAD


def test_non_dict_snapshot_item_returns_none():
    assert validate_remote_actors_snapshot_item("x") is None

