# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone
from profed.components.api.c2s.v1.timelines import projection
from profed.components.api.c2s.v1.timelines import storage as storage_module


NOTE_ID = "https://remote/notes/1"


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


def _payload(activity: dict, username: str = "alice") -> dict:
    return {"username": username, "activity": activity}


def test_inner_object_id_reads_a_referenced_object():
    assert projection._inner_object_id({"object": NOTE_ID}) == NOTE_ID


def test_inner_object_id_reads_an_embedded_object():
    assert projection._inner_object_id({"object": {"id": NOTE_ID, "content": "hi"}}) == NOTE_ID


def test_inner_object_id_without_object_is_none():
    assert projection._inner_object_id({"actor": "https://remote/bob"}) is None


def test_inner_object_id_of_embedded_object_without_id_is_none():
    assert projection._inner_object_id({"object": {"content": "hi"}}) is None


@pytest.mark.asyncio
async def test_create_stores_the_note_under_its_own_id(fake_storage):
    await projection._on_create("https://remote/activities/1",
                                _payload({"object": {"id": NOTE_ID, "content": "hi"}}))

    assert fake_storage.calls == [("add", ("alice", NOTE_ID,
                                           {"id": "https://remote/activities/1",
                                            "type": "Create",
                                            "object": {"id": NOTE_ID, "content": "hi"}}))]


@pytest.mark.asyncio
async def test_create_without_an_object_is_ignored(fake_storage):
    await projection._on_create("https://remote/activities/1", _payload({"actor": "https://remote/bob"}))

    assert fake_storage.calls == []


@pytest.mark.asyncio
async def test_update_replaces_the_stored_note(fake_storage):
    await projection._on_update("https://remote/activities/2",
                                _payload({"object": {"id": NOTE_ID, "content": "edited"}}))

    assert fake_storage.calls == [("update_status", ("alice", NOTE_ID,
                                                     {"id": "https://remote/activities/2",
                                                      "type": "Update",
                                                      "object": {"id": NOTE_ID, "content": "edited"}}))]


@pytest.mark.asyncio
async def test_update_without_an_object_is_ignored(fake_storage):
    await projection._on_update("https://remote/activities/2", _payload({"actor": "https://remote/bob"}))

    assert fake_storage.calls == []


@pytest.mark.asyncio
async def test_delete_removes_the_referenced_note(fake_storage):
    await projection._on_delete("https://remote/activities/3", _payload({"object": NOTE_ID}))

    assert fake_storage.calls == [("delete_status", ("alice", NOTE_ID))]


@pytest.mark.asyncio
async def test_delete_without_an_object_is_ignored(fake_storage):
    await projection._on_delete("https://remote/activities/3", _payload({"actor": "https://remote/bob"}))

    assert fake_storage.calls == []


@pytest.mark.asyncio
async def test_announce_stores_the_boost_under_the_activity_id(fake_storage):
    await projection._on_announce("https://remote/activities/4", _payload({"object": NOTE_ID}))

    assert fake_storage.calls == [("add", ("alice", "https://remote/activities/4",
                                           {"id": "https://remote/activities/4",
                                            "type": "Announce",
                                            "object": NOTE_ID}))]


@pytest.mark.asyncio
async def test_snapshot_item_stores_the_note_under_its_own_id(fake_storage):
    await projection._apply_item(_payload({"id": "https://remote/activities/1",
                                           "type": "Create",
                                           "object": {"id": NOTE_ID}}))

    assert fake_storage.calls == [("add", ("alice", NOTE_ID,
                                           {"id": "https://remote/activities/1",
                                            "type": "Create",
                                            "object": {"id": NOTE_ID}}))]


@pytest.mark.asyncio
async def test_snapshot_item_without_an_object_falls_back_to_the_activity_id(fake_storage):
    await projection._apply_item(_payload({"id": "https://remote/activities/5", "type": "Create"}))

    assert fake_storage.calls == [("add", ("alice", "https://remote/activities/5",
                                           {"id": "https://remote/activities/5", "type": "Create"}))]


@pytest.mark.asyncio
async def test_snapshot_item_without_any_id_is_ignored(fake_storage):
    await projection._apply_item(_payload({"type": "Create"}))

    assert fake_storage.calls == []


@pytest.mark.asyncio
async def test_rebuild_signals_rebuild_finished(fake_bus, fake_storage):
    fake_bus.topic("timeline").messages = []

    await projection.rebuild()

    assert ("rebuild_finished", ()) in fake_storage.calls


@pytest.mark.asyncio
async def test_create_from_the_timeline_topic_reaches_the_storage(fake_bus, fake_storage):
    fake_bus.topic("timeline").messages = [(1, "Create", "https://remote/activities/1",
                                            datetime.now(timezone.utc),
                                            _payload({"object": {"id": NOTE_ID, "content": "hi"}}))]

    await projection.rebuild()

    assert ("add", ("alice", NOTE_ID, {"id": "https://remote/activities/1",
                                       "type": "Create",
                                       "object": {"id": NOTE_ID, "content": "hi"}})) in fake_storage.calls

