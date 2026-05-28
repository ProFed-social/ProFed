# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.topics.incoming_activities_topic import (validate_incoming_activities_event,
                                                     validate_incoming_activities_snapshot_item)


PAYLOAD = {"username": "alice",
           "activity": {"actor": "https://remote/bob"}}


def test_valid_follow_event_returns_payload():
    payload = validate_incoming_activities_event("Follow", PAYLOAD)

    assert payload is not None
    assert payload["username"] == "alice"

def test_valid_create_event_returns_payload():
    assert validate_incoming_activities_event("Create", PAYLOAD) is not None

def test_unknown_verb_returns_none():
    assert validate_incoming_activities_event("Foo", PAYLOAD) is None

def test_non_dict_payload_returns_none():
    assert validate_incoming_activities_event("Follow", "x") is None

def test_missing_username_returns_none():
    bad = {"activity": {}}

    assert validate_incoming_activities_event("Follow", bad) is None

def test_empty_username_returns_none():
    bad = {"username": "", "activity": {}}

    assert validate_incoming_activities_event("Follow", bad) is None

def test_missing_activity_returns_none():
    bad = {"username": "alice"}

    assert validate_incoming_activities_event("Follow", bad) is None

def test_snapshot_item_is_always_none():
    assert validate_incoming_activities_snapshot_item({"username": "alice"}) is None

def test_snapshot_item_handles_none_input():
    assert validate_incoming_activities_snapshot_item(None) is None

