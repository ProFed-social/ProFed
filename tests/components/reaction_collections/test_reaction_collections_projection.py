# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from profed.components.reaction_collections import projection
from profed.components.reaction_collections import storage as storage_module


NOTE = "https://remote.example/notes/7"

REACTIONS = f"{NOTE}/emojiReactions"

LIKES = f"{NOTE}/likes"


class FakeStorage:
    def __init__(self):
        self.known = {}

    async def remember(self, object_url, collection_url):
        self.known[object_url] = collection_url

    async def forget(self, object_url):
        self.known.pop(object_url, None)


@pytest.fixture
def store():
    backup = storage_module._instance
    storage_module._instance = FakeStorage()
    yield storage_module._instance
    storage_module._instance = backup


def _create(**obj):
    return {"username": "alice",
            "activity": {"id": f"{NOTE}#create",
                         "type": "Create",
                         "object": {"id": NOTE, "type": "Note", **obj}}}


@pytest.mark.asyncio
async def test_a_note_with_a_collection_is_remembered(store):
    await projection._on_object(NOTE, _create(emojiReactions=REACTIONS))

    assert store.known == {NOTE: REACTIONS}


@pytest.mark.asyncio
async def test_emoji_reactions_win_over_likes(store):
    await projection._on_object(NOTE, _create(emojiReactions=REACTIONS, likes=LIKES))

    assert store.known == {NOTE: REACTIONS}


@pytest.mark.asyncio
async def test_a_note_without_a_collection_is_not_remembered(store):
    await projection._on_object(NOTE, _create())

    assert store.known == {}


@pytest.mark.asyncio
async def test_an_activity_without_an_embedded_object_is_not_remembered(store):
    await projection._on_object(NOTE, {"username": "alice", "activity": {"object": NOTE}})

    assert store.known == {}


@pytest.mark.asyncio
async def test_an_update_replaces_what_was_known(store):
    await projection._on_object(NOTE, _create(emojiReactions=REACTIONS))

    await projection._on_object(NOTE, _create(likes=LIKES))

    assert store.known == {NOTE: LIKES}


@pytest.mark.asyncio
async def test_a_deleted_note_is_forgotten(store):
    await projection._on_object(NOTE, _create(emojiReactions=REACTIONS))

    await projection._on_delete(NOTE, {"username": "alice"})

    assert store.known == {}

