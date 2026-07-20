# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone
from profed.components.person_activities import translator


TS = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _actor(username="alice"):
    base = f"https://example.com/actors/{username}"
    return {"@context": "https://www.w3.org/ns/activitystreams",
            "id": base,
            "type": "Person",
            "preferredUsername": username,
            "name": "Alice",
            "inbox": f"{base}/inbox",
            "outbox": f"{base}/outbox"}


def _msg(seq, event_type, object_id, payload, ts=TS):
    return (seq, event_type, object_id, ts, payload)


def _activities(fake_bus):
    return fake_bus.topic("raw_activities").published


@pytest.mark.asyncio
async def test_person_created_emits_create(fake_bus):
    actor = _actor()
    fake_bus.topic("person").messages = [_msg(1, "created", "alice", actor)]

    await translator.handle_person_events()

    published = _activities(fake_bus)
    assert len(published) == 1
    assert published[0]["event_type"] == "Create"
    assert published[0]["object_id"] == f"{actor['id']}#create"
    activity = published[0]["payload"]["activity"]
    assert published[0]["payload"]["username"] == "alice"
    assert activity["actor"] == actor["id"]
    assert activity["object"]["preferredUsername"] == "alice"


@pytest.mark.asyncio
async def test_person_updated_emits_update(fake_bus):
    actor = _actor()
    fake_bus.topic("person").messages = [_msg(1, "updated", "alice", actor)]

    await translator.handle_person_events()

    published = _activities(fake_bus)
    assert [p["event_type"] for p in published] == ["Update"]
    assert published[0]["object_id"] == f"{actor['id']}#update"
    assert published[0]["payload"]["activity"]["object"]["id"] == actor["id"]


@pytest.mark.asyncio
async def test_person_deleted_emits_delete(fake_bus):
    fake_bus.topic("person").messages = [_msg(1, "deleted", "alice", {})]

    await translator.handle_person_events()

    published = _activities(fake_bus)
    assert [p["event_type"] for p in published] == ["Delete"]
    activity = published[0]["payload"]["activity"]
    assert published[0]["payload"]["username"] == "alice"
    assert activity["actor"] == activity["object"]
    assert published[0]["object_id"] == f"{activity['object']}#delete"


@pytest.mark.asyncio
async def test_published_carried_into_create_object(fake_bus):
    actor = {**_actor(), "published": "2026-01-01T00:00:00+00:00"}
    fake_bus.topic("person").messages = [_msg(1, "created", "alice", actor)]

    await translator.handle_person_events()

    obj = _activities(fake_bus)[0]["payload"]["activity"]["object"]
    assert obj["published"] == "2026-01-01T00:00:00+00:00"


@pytest.mark.asyncio
async def test_each_person_event_emits_one_activity(fake_bus):
    fake_bus.topic("person").messages = [_msg(1, "created", "alice", _actor()),
                                         _msg(2, "updated", "alice", _actor()),
                                         _msg(3, "deleted", "alice", {})]

    await translator.handle_person_events()

    assert [p["event_type"] for p in _activities(fake_bus)] == ["Create", "Update", "Delete"]

