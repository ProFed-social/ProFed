# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.topics.known_accounts_topic import (validate_known_accounts_event,
                                                validate_known_accounts_snapshot_item)


def test_created_with_valid_id_returns_payload():
    payload = {"id": "123", "acct": "bob@remote.example"}

    assert validate_known_accounts_event("created", payload) == payload

def test_updated_with_valid_id_returns_payload():
    payload = {"id": "123"}

    assert validate_known_accounts_event("updated", payload) == payload


def test_created_without_id_returns_none():
    assert validate_known_accounts_event("created", {"acct": "bob@remote.example"}) is None


def test_created_with_empty_id_returns_none():
    assert validate_known_accounts_event("created", {"id": ""}) is None


def test_count_event_with_int_returns_payload():
    payload = {"count": 3}

    assert validate_known_accounts_event("followers_changed", payload) == payload


def test_count_event_with_bool_returns_none():
    assert validate_known_accounts_event("followers_changed", {"count": True}) is None


def test_count_event_without_count_returns_none():
    assert validate_known_accounts_event("statuses_changed", {}) is None


def test_deleted_returns_payload():
    assert validate_known_accounts_event("deleted", {}) == {}


def test_unknown_event_type_returns_none():
    assert validate_known_accounts_event("discovered", {"id": "1"}) is None


def test_non_dict_payload_returns_none():
    assert validate_known_accounts_event("created", "x") is None


def test_valid_snapshot_item_returns_item():
    item = {"id": "123", "acct": "bob@remote.example"}

    assert validate_known_accounts_snapshot_item(item) == item


def test_snapshot_item_without_id_returns_none():
    assert validate_known_accounts_snapshot_item({"acct": "bob@remote.example"}) is None



def test_non_dict_snapshot_item_returns_none():
    assert validate_known_accounts_snapshot_item("x") is None

