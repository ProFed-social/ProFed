# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone
from profed.identity import status_id
from profed.topics.statuses_topic import (delete_event,
                                          inner_object_id,
                                          reference_of,
                                          is_actor_object,
                                          is_undoable_object,
                                          object_key_of,
                                          reaction_emoji,
                                          reaction_event,
                                          status_event,
                                          undo_event,
                                          validate_statuses_event,
                                          validate_statuses_snapshot_item)


EMITTED_AT = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

NOTE_ID = "https://remote/notes/1"

PAYLOAD = {"username": "alice",
           "activity": {"actor": "https://remote/bob",
                        "object": {"id": NOTE_ID, "type": "Note", "content": "hi"}}}

VALID_PAYLOAD = {"username": "alice",
                 "status_id": NOTE_ID,
                 "actor_url": "https://remote/bob",
                 "status": {"id": "42", "content": "<p>hi</p>"}}


@pytest.mark.parametrize("verb", ["Create", "Update", "Delete", "Announce"])
def test_status_verbs_return_payload(verb):
    payload = validate_statuses_event(verb, VALID_PAYLOAD)
    assert payload is not None
    assert payload["username"] == "alice"


@pytest.mark.parametrize("verb", ["Follow", "Accept", "Reject", "Undo", "Block", "Tick"])
def test_non_status_verbs_are_rejected(verb):
    assert validate_statuses_event(verb, VALID_PAYLOAD) is None


def test_payload_must_be_a_dict():
    assert validate_statuses_event("Create", "nope") is None


def test_missing_username_is_rejected():
    assert validate_statuses_event("Create", {"status_id": NOTE_ID}) is None


def test_empty_username_is_rejected():
    assert validate_statuses_event("Create", {"username": "", "status_id": NOTE_ID}) is None


def test_missing_status_id_is_rejected():
    assert validate_statuses_event("Create", {"username": "alice"}) is None


def test_delete_without_status_is_accepted():
    payload = validate_statuses_event("Delete", {"username": "alice", "status_id": NOTE_ID})
    assert payload is not None
    assert payload["status"] is None


def test_snapshot_items_are_not_supported():
    assert validate_statuses_snapshot_item({"username": "alice"}) is None


def test_inner_object_id_reads_a_referenced_object():
    assert inner_object_id(NOTE_ID) == NOTE_ID


def test_inner_object_id_reads_an_embedded_object():
    assert inner_object_id({"id": NOTE_ID}) == NOTE_ID


def test_inner_object_id_without_object_is_none():
    assert inner_object_id(None) is None


def test_inner_object_id_of_embedded_object_without_id_is_none():
    assert inner_object_id({"content": "hi"}) is None


def test_is_actor_object_detects_a_person():
    assert is_actor_object({"id": "https://remote/bob", "type": "Person"}) is True


def test_is_actor_object_ignores_a_note():
    assert is_actor_object({"id": NOTE_ID, "type": "Note"}) is False


def test_object_key_of_announce_is_the_activity_id():
    assert object_key_of("Announce", "https://remote/bob#announce/1", {"object": NOTE_ID}) == \
        "https://remote/bob#announce/1"


def test_object_key_of_create_is_the_inner_object_id():
    assert object_key_of("Create", "https://remote/activities/1", {"object": NOTE_ID}) == NOTE_ID


def test_status_event_builds_an_account_less_status():
    event = status_event("Create", "https://remote/activities/1", PAYLOAD, EMITTED_AT, 7, own=False)
    assert event["username"] == "alice"
    assert event["status_id"] == NOTE_ID
    assert event["actor_url"] == "https://remote/bob"
    assert "account" not in event["status"]
    assert event["status"]["content"] == "hi"


def test_status_event_marks_the_origin_in_the_status_id():
    own = status_event("Create", "https://remote/activities/1", PAYLOAD, EMITTED_AT, 7, own=True)
    incoming = status_event("Create", "https://remote/activities/1", PAYLOAD, EMITTED_AT, 7, own=False)
    assert own["status"]["id"] == status_id(EMITTED_AT, 7, own=True)
    assert incoming["status"]["id"] == status_id(EMITTED_AT, 7, own=False)


def test_status_event_of_an_actor_object_is_none():
    payload = {"username": "alice",
               "activity": {"actor": "https://remote/bob",
                            "object": {"id": "https://remote/bob", "type": "Person"}}}
    assert status_event("Update", "https://remote/activities/1", payload, EMITTED_AT, 7, own=False) is None


def test_status_event_without_an_object_id_is_none():
    payload = {"username": "alice", "activity": {"object": {"content": "hi"}}}
    assert status_event("Create", "https://remote/activities/1", payload, EMITTED_AT, 7, own=False) is None


def test_delete_event_carries_only_the_object_key():
    payload = {"username": "alice", "activity": {"object": NOTE_ID}}
    assert delete_event("Delete", "https://remote/activities/1", payload) == \
        {"username": "alice", "status_id": NOTE_ID}


def test_delete_event_without_an_object_is_none():
    assert delete_event("Delete", "https://remote/activities/1", {"username": "alice", "activity": {}}) is None


def _event(event_type, activity):
    return status_event(event_type, activity.get("id", "https://remote/oid"),
                        {"username": "alice", "activity": activity}, EMITTED_AT, 1, own=False)


BOOST = {"actor": "https://remote/bob",
         "id": "https://remote/bob#announce/1",
         "type": "Announce",
         "object": "https://remote/notes/original"}

REPLY = {"actor": "https://remote/bob",
         "id": "https://remote/bob#create/1",
         "type": "Create",
         "object": {"id": "https://remote/notes/2",
                    "type": "Note",
                    "content": "re",
                    "inReplyTo": "https://remote/notes/parent"}}

POST = {"actor": "https://remote/bob",
        "id": "https://remote/bob#create/2",
        "type": "Create",
        "object": {"id": "https://remote/notes/3", "type": "Note", "content": "hi"}}


def test_a_boost_carries_an_announce_reference():
    assert _event("Announce", BOOST)["reference"] == {"kind": "announce", "url": "https://remote/notes/original"}


def test_a_reply_carries_a_reply_reference():
    assert _event("Create", REPLY)["reference"] == {"kind": "reply", "url": "https://remote/notes/parent"}


def test_an_ordinary_post_has_no_reference():
    assert _event("Create", POST)["reference"] is None


def test_reference_of_reads_a_boost_target():
    assert reference_of("Announce", BOOST) == {"kind": "announce", "url": "https://remote/notes/original"}


def test_reference_of_reads_a_reply_parent():
    assert reference_of("Create", REPLY) == {"kind": "reply", "url": "https://remote/notes/parent"}


def test_reference_of_an_ordinary_post_is_none():
    assert reference_of("Create", POST) is None


UNDO_ANNOUNCE = {"username": "alice",
                 "activity": {"actor": "https://local/actors/alice",
                              "object": {"id": "https://local/actors/alice#announce/7",
                                         "type": "Announce",
                                         "actor": "https://local/actors/alice",
                                         "object": "https://remote/notes/original"}}}

UNDO_FOLLOW = {"username": "alice",
               "activity": {"actor": "https://local/actors/alice",
                            "object": {"id": "https://local/actors/alice#follow/3",
                                       "type": "Follow",
                                       "actor": "https://local/actors/alice",
                                       "object": "https://remote/bob"}}}


def test_is_undoable_object_accepts_an_announce_activity():
    assert is_undoable_object(UNDO_ANNOUNCE["activity"]["object"]) is True


def test_is_undoable_object_accepts_a_like_and_an_emoji_react():
    assert is_undoable_object({"id": "https://remote/bob#like/3", "type": "Like"}) is True
    assert is_undoable_object({"id": "https://remote/bob#react/3", "type": "EmojiReact"}) is True


def test_is_undoable_object_rejects_a_follow():
    assert is_undoable_object(UNDO_FOLLOW["activity"]["object"]) is False


def test_is_undoable_object_rejects_a_string_reference():
    assert is_undoable_object("https://remote/notes/original") is False


def test_undo_event_removes_the_boost_by_its_announce_id():
    assert undo_event("Undo", "https://local/actors/alice#undo/9", UNDO_ANNOUNCE) == \
        {"username": "alice", "status_id": "https://local/actors/alice#announce/7"}


def test_undo_event_ignores_an_undone_follow():
    assert undo_event("Undo", "https://local/actors/alice#undo/9", UNDO_FOLLOW) is None


LIKE = {"username": "alice",
        "activity": {"actor": "https://remote/bob",
                     "object": "https://local/actors/alice/notes/1"}}

EMOJI_REACT = {"username": "alice",
               "activity": {"actor": "https://remote/bob",
                            "content": "🎉",
                            "object": "https://local/actors/alice/notes/1"}}

MISSKEY_LIKE = {"username": "alice",
                "activity": {"actor": "https://remote/bob",
                             "_misskey_reaction": "🐶",
                             "object": "https://local/actors/alice/notes/1"}}


def test_object_key_of_a_like_is_the_activity_itself():
    assert object_key_of("Like", "https://remote/bob#like/3", LIKE["activity"]) == "https://remote/bob#like/3"


def test_reaction_emoji_reads_the_content_of_an_emoji_react():
    assert reaction_emoji(EMOJI_REACT["activity"]) == "🎉"


def test_reaction_emoji_reads_the_misskey_attribute():
    assert reaction_emoji(MISSKEY_LIKE["activity"]) == "🐶"


def test_reaction_emoji_is_empty_for_a_plain_like():
    assert reaction_emoji(LIKE["activity"]) == ""


def test_reaction_event_points_at_the_reacted_object():
    event = reaction_event("EmojiReact", "https://remote/bob#react/3", EMOJI_REACT, EMITTED_AT, 7, False)

    assert event["status_id"] == "https://remote/bob#react/3"
    assert event["actor_url"] == "https://remote/bob"
    assert event["reference"] == {"kind": "like",
                                  "url": "https://local/actors/alice/notes/1",
                                  "emoji": "🎉"}


def test_reaction_event_carries_a_minimal_status_with_the_generated_id():
    event = reaction_event("Like", "https://remote/bob#like/3", LIKE, EMITTED_AT, 7, False)

    assert list(event["status"]) == ["id"]
    assert event["status"]["id"]


def test_reaction_event_ignores_a_reaction_without_an_object():
    assert reaction_event("Like", "https://remote/bob#like/3",
                          {"username": "alice", "activity": {"actor": "https://remote/bob"}},
                          EMITTED_AT, 7, False) is None


def test_reaction_event_ignores_a_reaction_to_an_actor():
    payload = {"username": "alice",
               "activity": {"actor": "https://remote/bob",
                            "object": {"id": "https://remote/carol", "type": "Person"}}}

    assert reaction_event("Like", "https://remote/bob#like/3", payload, EMITTED_AT, 7, False) is None


def test_like_is_an_accepted_status_verb():
    assert validate_statuses_event("Like", {"username": "alice",
                                            "status_id": "https://remote/bob#like/3",
                                            "actor_url": "https://remote/bob",
                                            "status": {"id": "42"}}) is not None


UNDO_LIKE = {"username": "alice",
             "activity": {"actor": "https://remote/bob",
                          "object": {"id": "https://remote/bob#like/3",
                                     "type": "Like",
                                     "actor": "https://remote/bob",
                                     "object": "https://local/actors/alice/notes/1"}}}


def test_undo_event_removes_the_reaction_by_its_activity_id():
    assert undo_event("Undo", "https://remote/bob#undo/9", UNDO_LIKE) == \
        {"username": "alice", "status_id": "https://remote/bob#like/3"}

