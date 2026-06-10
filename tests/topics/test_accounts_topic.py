# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.topics.accounts_topic import (validate_accounts_event,
                                          validate_accounts_snapshot_item)


def test_created_with_valid_id_returns_payload():
    payload = {"id": "123", "acct": "alice@example.com"}

    assert validate_accounts_event("created", payload) == payload


def test_updated_with_valid_id_returns_payload():
    payload = {"id": "123"}

    assert validate_accounts_event("updated", payload) == payload


def test_created_without_id_returns_none():
    assert validate_accounts_event("created", {"acct": "alice@example.com"}) is None


def test_created_with_empty_id_returns_none():
    assert validate_accounts_event("created", {"id": ""}) is None


def test_count_event_with_int_returns_payload():
    payload = {"count": 3}

    assert validate_accounts_event("followers_changed", payload) == payload


def test_count_event_with_bool_returns_none():
    assert validate_accounts_event("followers_changed", {"count": True}) is None


def test_count_event_without_count_returns_none():
    assert validate_accounts_event("statuses_changed", {}) is None


def test_deleted_returns_payload():
    assert validate_accounts_event("deleted", {}) == {}


def test_unknown_event_type_returns_none():
    assert validate_accounts_event("exploded", {"id": "1"}) is None


def test_non_dict_payload_returns_none():
    assert validate_accounts_event("created", "x") is None


def test_valid_snapshot_item_returns_item():
    item = {"id": "123", "acct": "alice@example.com"}

    assert validate_accounts_snapshot_item(item) == item


def test_snapshot_item_without_id_returns_none():
    assert validate_accounts_snapshot_item({"acct": "alice@example.com"}) is None


def test_non_dict_snapshot_item_returns_none():
    assert validate_accounts_snapshot_item("x") is None

