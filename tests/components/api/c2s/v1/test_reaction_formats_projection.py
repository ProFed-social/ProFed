# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from profed.components.api.c2s.v1.pleroma import projection
from profed.components.api.c2s.v1.pleroma import storage as storage_module


REACTION = "https://example.com/actors/alice#react/1"


class FakeStorage:
    def __init__(self):
        self.verbs = {}

    async def remember(self, reaction_url, verb):
        self.verbs[reaction_url] = verb

    async def forget(self, reaction_url):
        self.verbs.pop(reaction_url, None)


@pytest.fixture
def fake_storage():
    backup = storage_module._instance
    storage_module._instance = FakeStorage()
    yield storage_module._instance
    storage_module._instance = backup


def _undo(inner_type, inner_id=REACTION):
    return {"username": "alice", "activity": {"object": {"id": inner_id, "type": inner_type}}}


@pytest.mark.asyncio
async def test_an_emoji_react_is_remembered(fake_storage):
    await projection._remembered("EmojiReact", REACTION, {"username": "alice", "activity": {}})

    assert fake_storage.verbs == {REACTION: "EmojiReact"}


@pytest.mark.asyncio
async def test_a_like_is_remembered(fake_storage):
    await projection._remembered("Like", REACTION, {"username": "alice", "activity": {}})

    assert fake_storage.verbs == {REACTION: "Like"}


@pytest.mark.asyncio
async def test_an_emoji_react_is_registered_on_the_activities_topic(fake_bus, fake_storage):
    fake_bus.topic("activities").messages.append((1,
                                                  "EmojiReact",
                                                  REACTION,
                                                  None,
                                                  {"username": "alice", "activity": {"content": "🎉"}}))

    await projection.handle_events()

    assert fake_storage.verbs == {REACTION: "EmojiReact"}


@pytest.mark.asyncio
async def test_an_undone_reaction_is_forgotten(fake_storage):
    await projection._remembered("EmojiReact", REACTION, {"username": "alice", "activity": {}})

    await projection._forgotten("Undo", "https://example.com/actors/alice#undo/1", _undo("EmojiReact"))

    assert fake_storage.verbs == {}


@pytest.mark.asyncio
async def test_an_undone_boost_forgets_nothing(fake_storage):
    await projection._remembered("Like", REACTION, {"username": "alice", "activity": {}})

    await projection._forgotten("Undo", "https://example.com/actors/alice#undo/1", _undo("Announce"))

    assert fake_storage.verbs == {REACTION: "Like"}


@pytest.mark.asyncio
async def test_an_undo_without_an_inner_object_forgets_nothing(fake_storage):
    await projection._remembered("Like", REACTION, {"username": "alice", "activity": {}})

    await projection._forgotten("Undo",
                                "https://example.com/actors/alice#undo/1",
                                {"username": "alice", "activity": {"object": REACTION}})

    assert fake_storage.verbs == {REACTION: "Like"}

