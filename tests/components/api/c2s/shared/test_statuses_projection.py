# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone
from profed.components.api.c2s.shared.statuses import projection
from profed.components.api.c2s.shared.statuses import as_objects, user_timeline


NOTE_ID = "https://remote/notes/1"

ACTOR_URL = "https://remote/bob"

STATUS = {"id": "424242",
          "created_at": "2026-01-01T00:00:00.000Z",
          "uri": "https://remote/activities/1",
          "url": NOTE_ID,
          "content": "<p>hi</p>",
          "mentions": [],
          "tags": []}


class RecordingStorage:
    def __init__(self):
        self.calls: list[tuple] = []

    async def ensure_schema(self) -> None:
        self.calls.append(("ensure_schema", ()))

    async def upsert(self, *a):
        self.calls.append(("upsert", a))

    async def update_content(self, *a):
        self.calls.append(("update_content", a))

    async def delete(self, *a):
        self.calls.append(("delete", a))

    async def add(self, *a):
        self.calls.append(("add", a))

    async def remove_object(self, *a):
        self.calls.append(("remove_object", a))

    def rebuild_finished(self) -> None:
        self.calls.append(("rebuild_finished", ()))


@pytest.fixture
def fake_objects():
    backup = as_objects._instance
    as_objects._instance = RecordingStorage()
    yield as_objects._instance
    as_objects._instance = backup


@pytest.fixture
def fake_memberships():
    backup = user_timeline._instance
    user_timeline._instance = RecordingStorage()
    yield user_timeline._instance
    user_timeline._instance = backup


def _payload(status=STATUS, username="alice", actor_url=ACTOR_URL, reference=None, status_id=NOTE_ID):
    return {"username": username,
            "status_id": status_id,
            "actor_url": actor_url,
            "reference": reference,
            "status": status}


@pytest.mark.asyncio
async def test_create_upserts_the_content_object_and_adds_the_membership(fake_objects, fake_memberships):
    await projection._on_store("https://remote/activities/1", _payload())

    assert ("upsert", ("424242", NOTE_ID, ACTOR_URL, STATUS, "content", None, None)) in fake_objects.calls
    assert ("add", ("alice", NOTE_ID, "424242")) in fake_memberships.calls


@pytest.mark.asyncio
async def test_announce_upserts_a_boost_pointing_at_its_target(fake_objects, fake_memberships):
    announce = "https://remote/bob#announce/1"
    reference = {"kind": "announce", "url": NOTE_ID}

    await projection._on_store(announce, _payload(reference=reference, status_id=announce))

    assert ("upsert", ("424242", announce, ACTOR_URL, STATUS, "announce", NOTE_ID, None)) in fake_objects.calls
    assert ("add", ("alice", announce, "424242")) in fake_memberships.calls


@pytest.mark.asyncio
async def test_a_reply_reference_is_not_a_reblog(fake_objects, fake_memberships):
    reference = {"kind": "reply", "url": "https://remote/notes/0"}

    await projection._on_store("https://remote/activities/1", _payload(reference=reference))

    assert ("upsert", ("424242", NOTE_ID, ACTOR_URL, STATUS, "content", None, None)) in fake_objects.calls


@pytest.mark.asyncio
async def test_update_upserts_then_updates_content_and_leaves_membership_alone(fake_objects, fake_memberships):
    edited = {**STATUS, "content": "<p>edited</p>", "edited_at": "2026-02-02T00:00:00.000Z"}

    await projection._on_update("https://remote/activities/2", _payload(status=edited))

    assert ("upsert", ("424242", NOTE_ID, ACTOR_URL, edited, "content", None, None)) in fake_objects.calls
    assert ("update_content", (NOTE_ID, edited, "2026-02-02T00:00:00.000Z")) in fake_objects.calls
    assert all(call[0] != "add" for call in fake_memberships.calls)


@pytest.mark.asyncio
async def test_delete_removes_the_object_and_every_membership(fake_objects, fake_memberships):
    await projection._on_delete("https://remote/activities/3", {"username": "alice", "status_id": NOTE_ID})

    assert ("delete", (NOTE_ID,)) in fake_objects.calls
    assert ("remove_object", (NOTE_ID,)) in fake_memberships.calls


@pytest.mark.asyncio
async def test_snapshot_item_upserts_and_adds_the_membership(fake_objects, fake_memberships):
    await projection._apply_item(_payload())

    assert ("upsert", ("424242", NOTE_ID, ACTOR_URL, STATUS, "content", None, None)) in fake_objects.calls
    assert ("add", ("alice", NOTE_ID, "424242")) in fake_memberships.calls


@pytest.mark.asyncio
async def test_snapshot_item_without_an_actor_url_stores_an_empty_one(fake_objects, fake_memberships):
    await projection._apply_item({"username": "alice", "status_id": NOTE_ID, "status": STATUS})

    assert ("upsert", ("424242", NOTE_ID, "", STATUS, "content", None, None)) in fake_objects.calls


@pytest.mark.asyncio
async def test_rebuild_signals_both_storages(fake_bus, fake_objects, fake_memberships):
    fake_bus.topic("timeline").messages = []

    await projection.rebuild()

    assert ("rebuild_finished", ()) in fake_objects.calls
    assert ("rebuild_finished", ()) in fake_memberships.calls


@pytest.mark.asyncio
async def test_create_from_the_timeline_topic_reaches_both_storages(fake_bus, fake_objects, fake_memberships):
    fake_bus.topic("timeline").messages = [(1,
                                            "Create",
                                            "https://remote/activities/1",
                                            datetime.now(timezone.utc),
                                            _payload())]

    await projection.rebuild()

    assert ("upsert", ("424242", NOTE_ID, ACTOR_URL, STATUS, "content", None, None)) in fake_objects.calls
    assert ("add", ("alice", NOTE_ID, "424242")) in fake_memberships.calls


@pytest.mark.asyncio
async def test_a_like_reference_becomes_a_reaction_edge(fake_objects, fake_memberships):
    reference = {"kind": "like", "url": NOTE_ID, "emoji": "🎉"}
    like = "https://remote/bob#react/3"

    await projection._on_store(like, _payload(reference=reference, status_id=like))

    assert ("upsert", ("424242", like, ACTOR_URL, STATUS, "like", NOTE_ID, "🎉")) in fake_objects.calls


@pytest.mark.asyncio
async def test_a_like_without_an_emoji_keeps_the_edge(fake_objects, fake_memberships):
    reference = {"kind": "like", "url": NOTE_ID, "emoji": ""}
    like = "https://remote/bob#like/3"

    await projection._on_store(like, _payload(reference=reference, status_id=like))

    assert ("upsert", ("424242", like, ACTOR_URL, STATUS, "like", NOTE_ID, "")) in fake_objects.calls


@pytest.mark.asyncio
async def test_a_like_reference_becomes_a_reaction_edge(fake_objects, fake_memberships):
    reference = {"kind": "like", "url": NOTE_ID, "emoji": "🎉"}
    like = "https://remote/bob#react/3"

    await projection._on_store(like, _payload(reference=reference, status_id=like))

    assert ("upsert", ("424242", like, ACTOR_URL, STATUS, "like", NOTE_ID, "🎉")) in fake_objects.calls


@pytest.mark.asyncio
async def test_a_like_without_an_emoji_keeps_the_edge(fake_objects, fake_memberships):
    reference = {"kind": "like", "url": NOTE_ID, "emoji": ""}
    like = "https://remote/bob#like/3"

    await projection._on_store(like, _payload(reference=reference, status_id=like))

    assert ("upsert", ("424242", like, ACTOR_URL, STATUS, "like", NOTE_ID, "")) in fake_objects.calls


@pytest.mark.asyncio
async def test_a_like_from_the_timeline_topic_reaches_the_objects(fake_bus, fake_objects, fake_memberships):
    like = "https://remote/bob#react/3"
    fake_bus.topic("timeline").messages = [(1,
                                            "Like",
                                            like,
                                            datetime.now(timezone.utc),
                                            _payload(reference={"kind": "like", "url": NOTE_ID, "emoji": "🎉"},
                                                     status_id=like))]

    await projection.rebuild()

    assert ("upsert", ("424242", like, ACTOR_URL, STATUS, "like", NOTE_ID, "🎉")) in fake_objects.calls


@pytest.mark.asyncio
async def test_a_like_is_not_added_to_a_user_timeline(fake_bus, fake_objects, fake_memberships):
    like = "https://remote/bob#react/3"
    fake_bus.topic("timeline").messages = [(1,
                                            "Like",
                                            like,
                                            datetime.now(timezone.utc),
                                            _payload(reference={"kind": "like", "url": NOTE_ID, "emoji": "🎉"},
                                                     status_id=like))]

    await projection.rebuild()

    assert all(call[0] != "add" for call in fake_memberships.calls)

