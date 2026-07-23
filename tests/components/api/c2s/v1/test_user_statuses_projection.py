# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from profed.components.api.c2s.v1.accounts.statuses import storage as storage_module
from profed.components.api.c2s.v1.accounts.statuses import projection
from profed.core.message_bus.source_key import source_key


NOTE = "https://example.com/actors/alice/notes/1"
MASTODON_ID = str(source_key("activities").message_id(42).int)
STATUS = {"id": MASTODON_ID,
          "created_at": "2026-01-01T00:00:00.000Z",
          "uri": "https://example.com/actors/alice#create/1",
          "url": NOTE,
          "content": "<p>hi</p>",
          "mentions": [],
          "tags": []}


class FakeStatusStorage:
    def __init__(self):
        self.rows = {}

    async def ensure_schema(self):
        pass

    async def add(self, username, status_id, mastodon_id, status):
        self.rows.setdefault((username, status_id), {"mastodon_id": mastodon_id, "status": status})


    async def update_status(self, username, status_id, status):
        if (username, status_id) in self.rows:
            self.rows[(username, status_id)]["status"] = status

    async def delete_status(self, username, status_id):
        self.rows.pop((username, status_id), None)


@pytest.fixture
def fake_status_storage():
    backup = storage_module._instance
    storage_module._instance = FakeStatusStorage()
    yield storage_module._instance
    storage_module._instance = backup


@pytest.mark.asyncio
async def test_create_stores_the_status_content(fake_status_storage):
    await projection._on_store("https://example.com/actors/alice#create/1",
                               {"username": "alice", "status_id": NOTE, "status": STATUS})

    assert fake_status_storage.rows[("alice", NOTE)]["status"] == STATUS


@pytest.mark.asyncio
async def test_create_uses_the_status_id_as_sort_key(fake_status_storage):
    await projection._on_store("https://example.com/actors/alice#create/1",
                               {"username": "alice", "status_id": NOTE, "status": STATUS})

    assert fake_status_storage.rows[("alice", NOTE)]["mastodon_id"] == MASTODON_ID


@pytest.mark.asyncio
async def test_update_replaces_the_status_content(fake_status_storage):
    await projection._on_store("https://example.com/actors/alice#create/1",
                               {"username": "alice", "status_id": NOTE, "status": STATUS})
    await projection._on_update("https://example.com/actors/alice#update/1",
                                {"username": "alice",
                                 "status_id": NOTE,
                                 "status": {**STATUS, "content": "<p>edited</p>"}})

    assert fake_status_storage.rows[("alice", NOTE)]["status"]["content"] == "<p>edited</p>"


@pytest.mark.asyncio
async def test_update_keeps_the_sort_key(fake_status_storage):
    await projection._on_store("https://example.com/actors/alice#create/1",
                               {"username": "alice", "status_id": NOTE, "status": STATUS})
    await projection._on_update("https://example.com/actors/alice#update/1",
                                {"username": "alice",
                                 "status_id": NOTE,
                                 "status": {**STATUS, "content": "<p>edited</p>"}})

    assert fake_status_storage.rows[("alice", NOTE)]["mastodon_id"] == MASTODON_ID


@pytest.mark.asyncio
async def test_delete_removes_the_status(fake_status_storage):
    await projection._on_store("https://example.com/actors/alice#create/1",
                               {"username": "alice", "status_id": NOTE, "status": STATUS})
    await projection._on_delete("https://example.com/actors/alice#delete/1",
                                {"username": "alice", "status_id": NOTE})

    assert ("alice", NOTE) not in fake_status_storage.rows


@pytest.mark.asyncio
async def test_announce_stores_the_status_content(fake_status_storage):
    announce = "https://example.com/actors/alice#announce/1"
    await projection._on_store(announce,
                               {"username": "alice", "status_id": announce, "status": STATUS})

    assert fake_status_storage.rows[("alice", announce)]["status"] == STATUS


@pytest.mark.asyncio
async def test_snapshot_stores_the_status_content(fake_status_storage):
    await projection._apply_item({"username": "alice", "status_id": NOTE, "status": STATUS})

    assert fake_status_storage.rows[("alice", NOTE)]["status"] == STATUS

