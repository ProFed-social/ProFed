# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from profed.components.api.s2s.reactions import projection
from profed.components.api.s2s.reactions import storage as storage_module


NOTE = "https://example.com/actors/alice/notes/7"

REACTION = "https://r.example/users/bob#react/1"


class FakeStorage:
    def __init__(self):
        self.rows = {}

    async def record(self, reaction_url, object_url, actor_url, emoji, status_id):
        self.rows[reaction_url] = {"object_url": object_url,
                                   "actor_url": actor_url,
                                   "emoji": emoji,
                                   "status_id": status_id}

    async def forget(self, reaction_url):
        self.rows.pop(reaction_url, None)


@pytest.fixture
def fake_storage():
    backup = storage_module._instance
    storage_module._instance = FakeStorage()
    yield storage_module._instance
    storage_module._instance = backup


def _payload(**rest):
    return {"username": "alice",
            "status_id": REACTION,
            "actor_url": "https://r.example/users/bob",
            "reference": {"kind": "like", "url": NOTE, "emoji": "🎉"},
            "status": {"id": "110868037632009422"},
            **rest}


@pytest.mark.asyncio
async def test_a_reaction_is_recorded_against_its_target(fake_storage):
    await projection._on_react(REACTION, _payload())

    assert fake_storage.rows[REACTION] == {"object_url": NOTE,
                                           "actor_url": "https://r.example/users/bob",
                                           "emoji": "🎉",
                                           "status_id": 110868037632009422}


@pytest.mark.asyncio
async def test_a_bare_like_is_recorded_with_an_empty_emoji(fake_storage):
    await projection._on_react(REACTION, _payload(reference={"kind": "like", "url": NOTE}))

    assert fake_storage.rows[REACTION]["emoji"] == ""


@pytest.mark.asyncio
async def test_a_post_is_not_a_reaction(fake_storage):
    await projection._on_react(NOTE, _payload(reference={"kind": "content", "url": None}))

    assert fake_storage.rows == {}


@pytest.mark.asyncio
async def test_an_event_without_a_reference_is_not_a_reaction(fake_storage):
    await projection._on_react(NOTE, _payload(reference=None))

    assert fake_storage.rows == {}


@pytest.mark.asyncio
async def test_an_undone_reaction_is_forgotten(fake_storage):
    await projection._on_react(REACTION, _payload())

    await projection._on_delete(REACTION, {"username": "alice", "status_id": REACTION})

    assert fake_storage.rows == {}


@pytest.mark.asyncio
async def test_a_deleted_note_leaves_the_reactions_alone(fake_storage):
    await projection._on_react(REACTION, _payload())

    await projection._on_delete(NOTE, {"username": "alice", "status_id": NOTE})

    assert REACTION in fake_storage.rows


@pytest.mark.asyncio
async def test_a_changed_reaction_replaces_the_row(fake_storage):
    await projection._on_react(REACTION, _payload())

    await projection._on_react(REACTION, _payload(reference={"kind": "like", "url": NOTE, "emoji": "🐶"}))

    assert fake_storage.rows[REACTION]["emoji"] == "🐶"

