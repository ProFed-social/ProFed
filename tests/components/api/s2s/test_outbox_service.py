# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

from profed.components.api.s2s.outbox import storage
from profed.components.api.s2s.outbox import followers_storage
from profed.components.api.s2s.outbox.service import NotVisible, resolve_note, resolve_outbox


NOTE_URL = "https://example.com/actors/alice/notes/abc"

DELETED_AT = datetime(2026, 8, 24, 10, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def fake_storage():
    backup = (storage._instance, followers_storage._instance)
    storage._instance = Mock()
    storage._instance.latest_for_object = AsyncMock()
    followers_storage._instance = Mock(follows=AsyncMock(return_value=False))

    yield storage._instance

    storage._instance, followers_storage._instance = backup


@pytest.mark.asyncio
async def test_resolve_note_returns_the_note_object(fake_storage):
    note = {"id": NOTE_URL, "type": "Note", "content": "hi"}
    fake_storage.latest_for_object.return_value = {"type": "Create",
                                                   "object": note,
                                                   "created_at": DELETED_AT,
                                                   "visibility": "public",
                                                   "recipients": []}

    result = await resolve_note("alice", "abc")

    fake_storage.latest_for_object.assert_awaited_once_with("alice", NOTE_URL)
    assert {key: result[key] for key in note} == note


@pytest.mark.asyncio
async def test_resolve_note_points_at_its_reaction_collections(fake_storage):
    fake_storage.latest_for_object.return_value = {"type": "Create",
                                                   "object": {"id": NOTE_URL, "type": "Note", "content": "hi"},
                                                   "created_at": DELETED_AT,
                                                   "visibility": "public",
                                                   "recipients": []}

    result = await resolve_note("alice", "abc")

    assert result["likes"] == f"{NOTE_URL}/likes"
    assert result["emojiReactions"] == f"{NOTE_URL}/emojiReactions"


@pytest.mark.asyncio
async def test_the_note_context_explains_the_emoji_reactions_term(fake_storage):
    fake_storage.latest_for_object.return_value = {"type": "Create",
                                                   "object": {"id": NOTE_URL, "type": "Note", "content": "hi"},
                                                   "created_at": DELETED_AT,
                                                   "visibility": "public",
                                                   "recipients": []}

    result = await resolve_note("alice", "abc")

    assert result["@context"][-1] == {"emojiReactions": {"@id": "http://fedibird.com/ns#emojiReactions",
                                                         "@type": "@id"}}


@pytest.mark.asyncio
async def test_an_existing_context_is_kept(fake_storage):
    note = {"id": NOTE_URL, "type": "Note", "content": "hi", "@context": ["https://example.test/ns"]}
    fake_storage.latest_for_object.return_value = {"type": "Create",
                                                   "object": note,
                                                   "created_at": DELETED_AT,
                                                   "visibility": "public",
                                                   "recipients": []}

    assert (await resolve_note("alice", "abc"))["@context"][0] == "https://example.test/ns"


@pytest.mark.asyncio
async def test_a_single_context_becomes_a_list(fake_storage):
    note = {"id": NOTE_URL, "type": "Note", "content": "hi", "@context": "https://example.test/ns"}
    fake_storage.latest_for_object.return_value = {"type": "Create",
                                                   "object": note,
                                                   "created_at": DELETED_AT,
                                                   "visibility": "public",
                                                   "recipients": []}

    assert (await resolve_note("alice", "abc"))["@context"][:1] == ["https://example.test/ns"]


@pytest.mark.asyncio
async def test_a_tombstone_has_no_collections(fake_storage):
    fake_storage.latest_for_object.return_value = {"type": "Delete",
                                                   "object": NOTE_URL,
                                                   "created_at": DELETED_AT,
                                                   "visibility": "public",
                                                   "recipients": []}

    assert "likes" not in await resolve_note("alice", "abc")


@pytest.mark.asyncio
async def test_resolve_note_returns_the_edited_note_after_an_update(fake_storage):
    edited = {"id": NOTE_URL, "type": "Note", "content": "edited"}
    fake_storage.latest_for_object.return_value = {"type": "Update",
                                                   "object": edited,
                                                   "created_at": DELETED_AT,
                                                   "visibility": "public",
                                                   "recipients": []}

    assert (await resolve_note("alice", "abc"))["content"] == "edited"


@pytest.mark.asyncio
async def test_resolve_note_returns_a_tombstone_after_a_delete(fake_storage):
    fake_storage.latest_for_object.return_value = {"type": "Delete",
                                                   "object": NOTE_URL,
                                                   "created_at": DELETED_AT,
                                                   "visibility": "public",
                                                   "recipients": []}

    result = await resolve_note("alice", "abc")

    assert result == {"@context": "https://www.w3.org/ns/activitystreams",
                      "id": NOTE_URL,
                      "type": "Tombstone",
                      "deleted": "2026-08-24T10:00:00+00:00"}


@pytest.mark.asyncio
async def test_resolve_note_returns_none_for_an_unknown_note(fake_storage):
    fake_storage.latest_for_object.return_value = None

    assert await resolve_note("alice", "abc") is None


BOB = "https://r.example/users/bob"

SERVER = "https://r.example/actor"


@pytest.fixture
def outbox_and_followers():
    backup_outbox, backup_followers = storage._instance, followers_storage._instance
    storage._instance = Mock(fetch=AsyncMock(return_value=[]))
    followers_storage._instance = Mock(follows=AsyncMock(return_value=False))

    yield storage._instance, followers_storage._instance

    storage._instance, followers_storage._instance = backup_outbox, backup_followers


def _asked(outbox):
    return outbox.fetch.await_args.args[1:]


@pytest.mark.asyncio
async def test_an_unsigned_request_reaches_nothing_but_the_public(outbox_and_followers):
    outbox, _ = outbox_and_followers

    await resolve_outbox("alice")

    assert _asked(outbox) == ([], [], False)


@pytest.mark.asyncio
async def test_an_actor_key_reaches_what_is_addressed_to_it(outbox_and_followers):
    outbox, _ = outbox_and_followers

    await resolve_outbox("alice", {"actor_url": BOB, "actor_type": "Person"})

    assert _asked(outbox) == ([BOB], [], False)


@pytest.mark.asyncio
async def test_a_server_key_reaches_its_whole_host(outbox_and_followers):
    outbox, _ = outbox_and_followers

    await resolve_outbox("alice", {"actor_url": SERVER, "actor_type": "Application"})

    assert _asked(outbox) == ([SERVER], ["r.example"], False)


@pytest.mark.asyncio
async def test_a_following_signer_also_reaches_the_followers_only(outbox_and_followers):
    outbox, follower_edges = outbox_and_followers
    follower_edges.follows.return_value = True

    await resolve_outbox("alice", {"actor_url": BOB, "actor_type": "Person"})

    assert _asked(outbox) == ([BOB], [], True)


@pytest.mark.asyncio
async def test_the_author_is_the_one_whose_followers_are_asked_about(outbox_and_followers):
    _, follower_edges = outbox_and_followers

    await resolve_outbox("alice", {"actor_url": BOB, "actor_type": "Person"})

    assert follower_edges.follows.await_args.args[0] == "https://example.com/actors/alice"


@pytest.mark.asyncio
async def test_the_collection_counts_what_it_carries(outbox_and_followers):
    outbox, _ = outbox_and_followers
    outbox.fetch.return_value = [{"id": "https://example.com/a",
                                  "type": "Create",
                                  "actor": "https://example.com/actors/alice",
                                  "object": {"id": "https://example.com/notes/a"}},
                                 {"id": "https://example.com/b",
                                  "type": "Create",
                                  "actor": "https://example.com/actors/alice",
                                  "object": {"id": "https://example.com/notes/b"}}]

    assert (await resolve_outbox("alice")).totalItems == 2


@pytest.mark.asyncio
async def test_an_unknown_actor_class_reaches_no_host(outbox_and_followers):
    outbox, _ = outbox_and_followers

    await resolve_outbox("alice", {"actor_url": SERVER, "actor_type": "Robot"})

    assert _asked(outbox) == ([SERVER], [], False)


PRIVATE_NOTE = {"type": "Create",
                "object": {"id": NOTE_URL, "type": "Note", "content": "hi"},
                "created_at": DELETED_AT,
                "visibility": "direct",
                "recipients": [BOB]}


@pytest.mark.asyncio
async def test_a_directed_note_is_refused_to_a_stranger(fake_storage):
    fake_storage.latest_for_object.return_value = PRIVATE_NOTE

    with pytest.raises(NotVisible):
        await resolve_note("alice", "abc", {"actor_url": "https://r.example/users/eve", "actor_type": "Person"})


@pytest.mark.asyncio
async def test_a_directed_note_reaches_the_actor_it_names(fake_storage):
    fake_storage.latest_for_object.return_value = PRIVATE_NOTE

    result = await resolve_note("alice", "abc", {"actor_url": BOB, "actor_type": "Person"})

    assert result["id"] == NOTE_URL


@pytest.mark.asyncio
async def test_a_directed_note_reaches_the_server_of_its_recipient(fake_storage):
    fake_storage.latest_for_object.return_value = PRIVATE_NOTE

    result = await resolve_note("alice", "abc", {"actor_url": SERVER, "actor_type": "Application"})

    assert result["id"] == NOTE_URL


@pytest.mark.asyncio
async def test_a_followers_only_note_is_refused_to_a_stranger(fake_storage):
    fake_storage.latest_for_object.return_value = {**PRIVATE_NOTE, "visibility": "followers", "recipients": []}

    with pytest.raises(NotVisible):
        await resolve_note("alice", "abc", {"actor_url": BOB, "actor_type": "Person"})


@pytest.mark.asyncio
async def test_a_followers_only_note_reaches_a_follower(fake_storage):
    fake_storage.latest_for_object.return_value = {**PRIVATE_NOTE, "visibility": "followers", "recipients": []}
    followers_storage._instance.follows.return_value = True

    result = await resolve_note("alice", "abc", {"actor_url": BOB, "actor_type": "Person"})

    assert result["id"] == NOTE_URL


@pytest.mark.asyncio
async def test_a_note_that_does_not_exist_is_not_refused_but_missing(fake_storage):
    fake_storage.latest_for_object.return_value = None

    assert await resolve_note("alice", "abc") is None


