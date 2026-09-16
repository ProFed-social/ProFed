# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import pytest
from profed.components.reaction_collections import projection
from profed.components.reaction_collections import storage as storage_module
from profed.core.config import config as profed_config, raw


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


@pytest.fixture(autouse=True)
def our_domain():
    raw.paths = []
    raw.argv = ["", "--profed.run=api", "--web-server.domain=example.com"]
    os.environ = {k: v for k, v in os.environ.items() if not k.startswith("PROFED_")}
    profed_config.reset()
    yield
    profed_config.reset()


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
async def test_a_note_with_a_collection_is_remembered(fake_bus, store):
    await projection._on_object(NOTE, _create(emojiReactions=REACTIONS))

    assert store.known == {NOTE: REACTIONS}


@pytest.mark.asyncio
async def test_emoji_reactions_win_over_likes(fake_bus, store):
    await projection._on_object(NOTE, _create(emojiReactions=REACTIONS, likes=LIKES))

    assert store.known == {NOTE: REACTIONS}


@pytest.mark.asyncio
async def test_a_note_without_a_collection_is_not_remembered(fake_bus, store):
    await projection._on_object(NOTE, _create())

    assert store.known == {}


@pytest.mark.asyncio
async def test_an_activity_without_an_embedded_object_is_not_remembered(fake_bus, store):
    await projection._on_object(NOTE, {"username": "alice", "activity": {"object": NOTE}})

    assert store.known == {}


@pytest.mark.asyncio
async def test_an_update_replaces_what_was_known(fake_bus, store):
    await projection._on_object(NOTE, _create(emojiReactions=REACTIONS))

    await projection._on_object(NOTE, _create(likes=LIKES))

    assert store.known == {NOTE: LIKES}


@pytest.mark.asyncio
async def test_a_remembered_note_is_asked_for_right_away(fake_bus, store):
    await projection._on_object(NOTE, _create(emojiReactions=REACTIONS))
 
    published = fake_bus.topic("reaction_refresh").published
    assert published[0]["event_type"] == "requested"
    assert published[0]["payload"]["object_urls"] == [NOTE]
 
 
@pytest.mark.asyncio
async def test_a_note_of_our_own_is_neither_remembered_nor_asked_for(fake_bus, store):
    ours = "https://example.com/notes/3"
    payload = {"username": "alice",
               "activity": {"id": f"{ours}#create",
                            "type": "Create",
                            "object": {"id": ours,
                                       "type": "Note",
                                       "emojiReactions": f"{ours}/emojiReactions"}}}
 
    await projection._on_object(ours, payload)
 
    assert store.known == {}
    assert fake_bus.topic("reaction_refresh").published == []
 
 
@pytest.mark.asyncio
async def test_a_note_without_a_collection_is_not_asked_for(fake_bus, store):
    await projection._on_object(NOTE, _create())
 
    assert fake_bus.topic("reaction_refresh").published == []


@pytest.mark.asyncio
async def test_a_deleted_note_is_forgotten(fake_bus, store):
    await projection._on_object(NOTE, _create(emojiReactions=REACTIONS))

    await projection._on_delete(NOTE, {"username": "alice"})

    assert store.known == {}

