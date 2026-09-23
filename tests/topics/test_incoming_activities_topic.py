# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from pydantic import ValidationError
from profed.topics.incoming_activities_topic import (canonical_incoming,
                                                     publish_incoming,
                                                     validate_incoming_activities_event,
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


def test_empty_username_is_accepted_for_fetched_objects():
    fetched = {"username": "", "activity": {"actor": "https://remote/bob"}}

    assert validate_incoming_activities_event("Create", fetched) is not None


def test_missing_activity_returns_none():
    bad = {"username": "alice"}

    assert validate_incoming_activities_event("Follow", bad) is None


def test_snapshot_item_is_always_none():
    assert validate_incoming_activities_snapshot_item({"username": "alice"}) is None


def test_snapshot_item_handles_none_input():
    assert validate_incoming_activities_snapshot_item(None) is None


async def test_publish_incoming_publishes_the_activity(fake_bus):
    await publish_incoming("Create", "https://remote/notes/1", "alice", {"actor": "https://remote/bob"})

    published = fake_bus.topic("incoming_activities").published
    assert len(published) == 1
    assert published[0]["event_type"] == "Create"
    assert published[0]["object_id"] == "https://remote/notes/1"
    assert published[0]["payload"] == {"username": "alice", "activity": {"actor": "https://remote/bob"}}


async def test_publish_incoming_does_not_sanitize(fake_bus):
    await publish_incoming("Create", "https://remote/notes/1", "alice", {"content": "<script>x</script>"})

    published = fake_bus.topic("incoming_activities").published
    assert published[0]["payload"]["activity"]["content"] == "<script>x</script>"


def test_emoji_react_is_a_known_verb():
    assert validate_incoming_activities_event("EmojiReact",
                                              {"username": "alice",
                                               "activity": {"actor": "https://remote/bob",
                                                            "object": "https://local/notes/1"}}) is not None


def test_the_canonical_form_splits_off_type_and_id():
    assert canonical_incoming({"id": "https://example.com/follows/1",
                               "type": "Follow",
                               "actor": "https://example.com/actors/bob"}) == \
           ("Follow", "https://example.com/follows/1", {"actor": "https://example.com/actors/bob"})


def test_the_canonical_form_is_sanitized():
    _, _, activity = canonical_incoming({"id": "https://example.com/notes/1",
                                         "type": "Create",
                                         "object": {"content": "<p>hi</p><script>alert(1)</script>"}})

    assert "<script>" not in activity["object"]["content"]


def test_a_malformed_actor_is_refused():
    with pytest.raises(ValidationError):
        canonical_incoming({"id": "https://example.com/follows/1", "type": "Follow", "actor": 42})

