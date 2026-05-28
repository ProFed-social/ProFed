# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
from profed.topics.activities_topic import (validate_activities_event,
                                            validate_activities_snapshot_item)

PAYLOAD = {"username": "alice",
           "activity": {"actor": "https://example.com/alice"}}

def test_valid_create_event_returns_payload():
    payload = validate_activities_event("Create", PAYLOAD)

    assert payload is not None
    assert payload["username"] == "alice"


def test_valid_follow_event_returns_payload():
    assert validate_activities_event("Follow", PAYLOAD) is not None


def test_valid_announce_event_returns_payload():
    assert validate_activities_event("Announce", PAYLOAD) is not None


def test_unknown_verb_returns_none():
    assert validate_activities_event("Foo", PAYLOAD) is None


def test_non_dict_payload_returns_none():
    assert validate_activities_event("Create", "not a dict") is None


def test_missing_username_returns_none():
    assert validate_activities_event("Create", {"activity": {}}) is None


def test_empty_username_returns_none():
    bad = {"username": "", "activity": {}}

    assert validate_activities_event("Create", bad) is None


def test_missing_activity_returns_none():
    assert validate_activities_event("Create", {"username": "alice"}) is None


def test_non_dict_activity_returns_none():
    bad = {"username": "alice", "activity": "not a dict"}

    assert validate_activities_event("Create", bad) is None


def test_valid_snapshot_item_returns_item():
    assert validate_activities_snapshot_item(PAYLOAD) == PAYLOAD


def test_invalid_snapshot_item_returns_none():
    assert validate_activities_snapshot_item({"username": "alice"}) is None

