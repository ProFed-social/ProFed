# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from profed.components.api.c2s.v1.accounts.statuses import storage as storage_module
from profed.components.api.c2s.v1.accounts.statuses import projection


class FakeStatusStorage:
    def __init__(self):
        self.rows = {}

    async def ensure_schema(self):
        pass

    async def add(self, username, status_id, sequence_id, activity):
        self.rows.setdefault((username, status_id),
                             {"sequence_id": sequence_id, "activity": activity})

    async def update_status(self, username, status_id, activity):
        if (username, status_id) in self.rows:
            self.rows[(username, status_id)]["activity"] = activity

    async def delete_status(self, username, status_id):
        self.rows.pop((username, status_id), None)


@pytest.fixture
def fake_status_storage():
    backup = storage_module._instance
    storage_module._instance = FakeStatusStorage()
    yield storage_module._instance
    storage_module._instance = backup


@pytest.mark.asyncio
async def test_create_stores_sequence_id(fake_status_storage):
    await projection._on_create("https://example.com/actors/alice#create/1",
                                {"username": "alice",
                                 "activity": {"actor": "https://example.com/actors/alice",
                                              "object": {"id": "https://example.com/actors/alice/notes/1",
                                                         "content": "<p>hi</p>"}}},
                                42)

    row = fake_status_storage.rows[("alice", "https://example.com/actors/alice/notes/1")]
    assert row["sequence_id"] == 42
    assert row["activity"]["type"] == "Create"
    assert row["activity"]["object"]["content"] == "<p>hi</p>"


@pytest.mark.asyncio
async def test_update_keeps_sequence_id_and_changes_content(fake_status_storage):
    note = "https://example.com/actors/alice/notes/1"
    await projection._on_create("https://example.com/actors/alice#create/1",
                                {"username": "alice",
                                 "activity": {"object": {"id": note, "content": "<p>original</p>"}}},
                                42)
    await projection._on_update("https://example.com/actors/alice#update/1",
                                {"username": "alice",
                                 "activity": {"object": {"id": note, "content": "<p>edited</p>"}}},
                                99)

    row = fake_status_storage.rows[("alice", note)]
    assert row["sequence_id"] == 42
    assert row["activity"]["object"]["content"] == "<p>edited</p>"


@pytest.mark.asyncio
async def test_delete_removes_status(fake_status_storage):
    note = "https://example.com/actors/alice/notes/1"

    await projection._on_create("https://example.com/actors/alice#create/1",
                                {"username": "alice", "activity": {"object": {"id": note}}},
                                1)
    await projection._on_delete("https://example.com/actors/alice#delete/1",
                                {"username": "alice", "activity": {"object": note}},
                                2)

    assert ("alice", note) not in fake_status_storage.rows


@pytest.mark.asyncio
async def test_announce_uses_announce_id_and_sequence(fake_status_storage):
    announce = "https://example.com/actors/alice#announce/1"

    await projection._on_announce(announce,
                                  {"username": "alice",
                                   "activity": {"object": "https://remote.example/notes/9"}},
                                  7)

    row = fake_status_storage.rows[("alice", announce)]
    assert row["sequence_id"] == 7
    assert row["activity"]["type"] == "Announce"

