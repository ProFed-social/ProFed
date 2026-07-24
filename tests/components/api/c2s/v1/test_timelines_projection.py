# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone
from profed.components.api.c2s.v1.timelines import projection
from profed.components.api.c2s.v1.timelines import storage as storage_module


NOTE_ID = "https://remote/notes/1"

ACTOR_URL = "https://remote/bob"

STATUS = {"id": "424242",
          "created_at": "2026-01-01T00:00:00.000Z",
          "uri": "https://remote/activities/1",
          "url": NOTE_ID,
          "content": "<p>hi</p>",
          "mentions": [],
          "tags": []}


class FakeStorage:
    def __init__(self):
        self.calls: list[tuple] = []

    async def ensure_schema(self) -> None:
        self.calls.append(("ensure_schema", ()))

    async def add(self, *a):
        self.calls.append(("add", a))

    async def update_status(self, *a):
        self.calls.append(("update_status", a))

    async def delete_status(self, *a):
        self.calls.append(("delete_status", a))

    def rebuild_finished(self) -> None:
        self.calls.append(("rebuild_finished", ()))


@pytest.fixture
def fake_storage():
    backup = storage_module._instance
    storage_module._instance = FakeStorage()
    yield storage_module._instance
    storage_module._instance = backup


def _payload(status=STATUS, username="alice", actor_url=ACTOR_URL):
    return {"username": username, "status_id": NOTE_ID, "actor_url": actor_url, "status": status}


@pytest.mark.asyncio
async def test_create_stores_the_status_under_its_object_id(fake_storage):
    await projection._on_store("https://remote/activities/1", _payload())

    assert ("add", ("alice", NOTE_ID, "424242", ACTOR_URL, STATUS)) in fake_storage.calls


@pytest.mark.asyncio
async def test_create_uses_the_status_id_as_sort_key(fake_storage):
    await projection._on_store("https://remote/activities/1", _payload())

    assert fake_storage.calls[0][1][2] == "424242"


@pytest.mark.asyncio
async def test_create_keeps_the_actor_url_for_the_account_join(fake_storage):
    await projection._on_store("https://remote/activities/1", _payload())

    assert fake_storage.calls[0][1][3] == ACTOR_URL


@pytest.mark.asyncio
async def test_update_replaces_the_stored_status(fake_storage):
    edited = {**STATUS, "content": "<p>edited</p>"}

    await projection._on_update("https://remote/activities/2", _payload(status=edited))

    assert ("update_status", ("alice", NOTE_ID, edited)) in fake_storage.calls


@pytest.mark.asyncio
async def test_delete_removes_the_referenced_status(fake_storage):
    await projection._on_delete("https://remote/activities/3", {"username": "alice", "status_id": NOTE_ID})

    assert ("delete_status", ("alice", NOTE_ID)) in fake_storage.calls


@pytest.mark.asyncio
async def test_announce_stores_the_boost(fake_storage):
    announce = "https://remote/bob#announce/1"
    payload = {"username": "alice", "status_id": announce, "actor_url": ACTOR_URL, "status": STATUS}

    await projection._on_store(announce, payload)

    assert ("add", ("alice", announce, "424242", ACTOR_URL, STATUS)) in fake_storage.calls


@pytest.mark.asyncio
async def test_snapshot_item_stores_the_status(fake_storage):
    await projection._apply_item(_payload())

    assert ("add", ("alice", NOTE_ID, "424242", ACTOR_URL, STATUS)) in fake_storage.calls


@pytest.mark.asyncio
async def test_snapshot_item_without_an_actor_url_stores_an_empty_one(fake_storage):
    await projection._apply_item({"username": "alice", "status_id": NOTE_ID, "status": STATUS})

    assert fake_storage.calls[0][1][3] == ""


@pytest.mark.asyncio
async def test_rebuild_signals_rebuild_finished(fake_bus, fake_storage):
    fake_bus.topic("timeline").messages = []

    await projection.rebuild()

    assert ("rebuild_finished", ()) in fake_storage.calls


@pytest.mark.asyncio
async def test_create_from_the_timeline_topic_reaches_the_storage(fake_bus, fake_storage):
    fake_bus.topic("timeline").messages = [(1,
                                            "Create",
                                            "https://remote/activities/1",
                                            datetime.now(timezone.utc),
                                            _payload())]

    await projection.rebuild()

    assert ("add", ("alice", NOTE_ID, "424242", ACTOR_URL, STATUS)) in fake_storage.calls

