# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import patch
from profed import identity
from profed.components.polish_activities import person
from profed.components.polish_activities import storage as storage_module


class FakeStorage:
    def __init__(self):
        self.remembered = []
        self.forgotten = []

    async def remember_actor(self, acct, actor_url):
        self.remembered.append((acct, actor_url))

    async def forget_actor(self, acct):
        self.forgotten.append(acct)


@pytest.fixture(autouse=True)
def store():
    backup = storage_module._instance
    storage_module._instance = FakeStorage()
    with patch.object(identity, "domain", lambda: "local.test"):
        yield storage_module._instance
    storage_module._instance = backup


@pytest.mark.asyncio
async def test_a_created_person_becomes_known(store):
    await person._person_changed("alice", {"id": "https://local.test/actors/alice"})

    assert store.remembered == [("alice@local.test", "https://local.test/actors/alice")]


@pytest.mark.asyncio
async def test_an_updated_person_is_remembered_again(store):
    await person._person_changed("alice", {"id": "https://local.test/actors/alice2"})

    assert store.remembered[0][1] == "https://local.test/actors/alice2"


@pytest.mark.asyncio
async def test_a_deleted_person_is_forgotten(store):
    await person._person_deleted("alice", {"id": "https://local.test/actors/alice"})

    assert store.forgotten == ["alice@local.test"]

