# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from profed.components.api.c2s.shared.bookmarks import projection
from profed.components.api.c2s.shared.bookmarks import storage as storage_module


ALICE = "https://example.com/actors/alice"

NOTE = "https://remote.example/notes/7"

MARK = {"actor_url": ALICE, "object_url": NOTE}


class FakeStorage:
    def __init__(self):
        self.marks = {}

    async def add(self, actor_url, object_url, marked_at):
        self.marks.setdefault((actor_url, object_url), marked_at)

    async def remove(self, actor_url, object_url):
        self.marks.pop((actor_url, object_url), None)


@pytest.fixture
def store():
    backup = storage_module._instance
    storage_module._instance = FakeStorage()
    yield storage_module._instance
    storage_module._instance = backup


@pytest.mark.asyncio
async def test_an_added_bookmark_is_kept_with_the_sequence_as_its_moment(store):
    await projection._on_added(f"{ALICE}|{NOTE}", MARK, 500)

    assert store.marks == {(ALICE, NOTE): 500}


@pytest.mark.asyncio
async def test_a_removed_bookmark_is_gone(store):
    await projection._on_added(f"{ALICE}|{NOTE}", MARK, 500)

    await projection._on_removed(f"{ALICE}|{NOTE}", MARK, 600)

    assert store.marks == {}


@pytest.mark.asyncio
async def test_removing_what_was_never_marked_is_quiet(store):
    await projection._on_removed(f"{ALICE}|{NOTE}", MARK, 600)

    assert store.marks == {}


@pytest.mark.asyncio
async def test_two_actors_keep_their_own_bookmarks(store):
    bob = "https://example.com/actors/bob"

    await projection._on_added(f"{ALICE}|{NOTE}", MARK, 500)
    await projection._on_added(f"{bob}|{NOTE}", {"actor_url": bob, "object_url": NOTE}, 600)
    await projection._on_removed(f"{ALICE}|{NOTE}", MARK, 700)

    assert store.marks == {(bob, NOTE): 600}


@pytest.mark.asyncio
async def test_a_snapshot_item_is_restored_with_its_moment(store):
    await projection._apply_item({**MARK, "marked_at": 500})

    assert store.marks == {(ALICE, NOTE): 500}

