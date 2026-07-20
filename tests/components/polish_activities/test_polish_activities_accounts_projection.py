# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from profed.components.polish_activities import storage as storage_module
from profed.components.polish_activities import accounts_projection as projection


class FakeStorage:
    def __init__(self):
        self.usernames = set()

    async def ensure_schema(self):
        pass

    async def add(self, username):
        self.usernames.add(username)

    async def delete(self, username):
        self.usernames.discard(username)


@pytest.fixture
def fake_storage():
    backup = storage_module._instance
    storage_module._instance = FakeStorage()
    yield storage_module._instance
    storage_module._instance = backup


@pytest.mark.asyncio
async def test_created_adds_local_username(fake_storage):
    await projection._present("alice", {"id": "alice"})
    assert "alice" in fake_storage.usernames


@pytest.mark.asyncio
async def test_updated_keeps_local_username(fake_storage):
    await projection._present("alice", {"id": "alice"})
    await projection._present("alice", {"id": "alice"})
    assert fake_storage.usernames == {"alice"}


@pytest.mark.asyncio
async def test_deleted_removes_local_username(fake_storage):
    await projection._present("alice", {"id": "alice"})
    await projection._deleted("alice", {})
    assert "alice" not in fake_storage.usernames


@pytest.mark.asyncio
async def test_snapshot_adds_local_username(fake_storage):
    await projection._apply_snapshot_item({"username": "alice"})
    assert "alice" in fake_storage.usernames

