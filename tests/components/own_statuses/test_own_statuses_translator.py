# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import profed.components.own_statuses.translator as mod
from profed.core.message_bus.source_key import source_key


NOTE_PAYLOAD = {"username": "alice",
                "activity": {"actor": "https://local/actors/alice",
                             "object": {"id": "https://local/notes/1",
                                        "type": "Note",
                                        "url": "https://local/notes/1",
                                        "published": "2026-01-01T00:00:00.000Z",
                                        "content": "hi"}}}

DELETE_PAYLOAD = {"username": "alice",
                  "activity": {"actor": "https://local/actors/alice",
                               "object": "https://local/notes/1"}}

PERSON_PAYLOAD = {"username": "alice",
                  "activity": {"actor": "https://local/actors/alice",
                               "object": {"id": "https://local/actors/alice",
                                          "type": "Person",
                                          "name": "Alice"}}}

UNIDENTIFIED_PAYLOAD = {"username": "alice",
                        "activity": {"actor": "https://local/actors/alice",
                                     "object": {"type": "Note", "content": "hi"}}}


def _fake_bus():
    published = []

    async def _publish(**kwargs):
        published.append(kwargs)

    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=_publish)
    ctx.__aexit__ = AsyncMock(return_value=False)
    topic = MagicMock()
    topic.publish = MagicMock(return_value=ctx)
    bus = MagicMock()
    bus.topic = MagicMock(return_value=topic)
    return bus, published


@pytest.mark.asyncio
async def test_create_publishes_status_content_to_statuses():
    bus, published = _fake_bus()

    with patch.object(mod, "message_bus", return_value=bus):
        await mod._convert("Create", "https://local/notes/1#create", NOTE_PAYLOAD, 7)

    assert bus.topic.call_args[0][0] == "statuses"
    assert len(published) == 1
    assert published[0]["event_type"] == "Create"
    assert published[0]["payload"]["username"] == "alice"
    assert published[0]["payload"]["status_id"] == "https://local/notes/1"
    assert published[0]["payload"]["status"]["content"] == "hi"
    assert published[0]["payload"]["status"]["url"] == "https://local/notes/1"


@pytest.mark.asyncio
async def test_create_omits_the_account_from_the_status_content():
    bus, published = _fake_bus()

    with patch.object(mod, "message_bus", return_value=bus):
        await mod._convert("Create", "https://local/notes/1#create", NOTE_PAYLOAD, 7)

    assert "account" not in published[0]["payload"]["status"]


@pytest.mark.asyncio
async def test_create_numbers_the_status_id_from_the_activities_sequence():
    bus, published = _fake_bus()

    with patch.object(mod, "message_bus", return_value=bus):
        await mod._convert("Create", "https://local/notes/1#create", NOTE_PAYLOAD, 42)

    assert published[0]["payload"]["status"]["id"] == str(source_key("activities").message_id(42).int)
    assert published[0]["payload"]["status"]["id"].isdigit()


@pytest.mark.asyncio
async def test_create_derives_message_id_from_the_activities_sequence():
    bus, published = _fake_bus()

    with patch.object(mod, "message_bus", return_value=bus):
        await mod._convert("Create", "https://local/notes/1#create", NOTE_PAYLOAD, 42)

    assert published[0]["message_id"] == source_key("activities").message_id(42)


@pytest.mark.asyncio
async def test_create_skips_activities_without_an_object_id():
    bus, published = _fake_bus()

    with patch.object(mod, "message_bus", return_value=bus):
        await mod._convert("Create", "https://local/notes/1#create", UNIDENTIFIED_PAYLOAD, 7)

    assert published == []


@pytest.mark.asyncio
async def test_create_skips_actor_objects():
    bus, published = _fake_bus()

    with patch.object(mod, "message_bus", return_value=bus):
        await mod._convert("Create", "https://local/actors/alice#create", PERSON_PAYLOAD, 7)

    assert published == []


@pytest.mark.asyncio
async def test_update_publishes_status_content():
    bus, published = _fake_bus()

    with patch.object(mod, "message_bus", return_value=bus):
        await mod._convert("Update", "https://local/notes/1#update", NOTE_PAYLOAD, 7)

    assert published[0]["event_type"] == "Update"
    assert published[0]["payload"]["status_id"] == "https://local/notes/1"


@pytest.mark.asyncio
async def test_update_skips_actor_objects():
    bus, published = _fake_bus()

    with patch.object(mod, "message_bus", return_value=bus):
        await mod._convert("Update", "https://local/actors/alice#update", PERSON_PAYLOAD, 7)

    assert published == []


@pytest.mark.asyncio
async def test_delete_publishes_only_the_status_id():
    bus, published = _fake_bus()

    with patch.object(mod, "message_bus", return_value=bus):
        await mod._convert_delete("Delete", "https://local/notes/1#delete", DELETE_PAYLOAD, 7)

    assert published[0]["event_type"] == "Delete"
    assert published[0]["payload"] == {"username": "alice",
                                       "status_id": "https://local/notes/1"}


@pytest.mark.asyncio
async def test_delete_skips_activities_without_an_object_id():
    payload = {"username": "alice", "activity": {"actor": "https://local/actors/alice"}}
    bus, published = _fake_bus()

    with patch.object(mod, "message_bus", return_value=bus):
        await mod._convert_delete("Delete", "https://local/notes/1#delete", payload, 7)

    assert published == []


@pytest.mark.asyncio
async def test_announce_uses_the_activity_id_as_status_id():
    bus, published = _fake_bus()

    with patch.object(mod, "message_bus", return_value=bus):
        await mod._convert("Announce", "https://local/actors/alice#announce/1", NOTE_PAYLOAD, 7)

    assert published[0]["event_type"] == "Announce"
    assert published[0]["payload"]["status_id"] == "https://local/actors/alice#announce/1"


@pytest.mark.asyncio
async def test_create_activities_are_converted_on_rebuild(fake_bus):
    fake_bus.topic("activities").messages = [(1,
                                              "Create",
                                              "https://local/notes/1#create",
                                              datetime.now(timezone.utc),
                                              NOTE_PAYLOAD)]

    await mod.rebuild()

    published = fake_bus.topic("statuses").published
    assert len(published) == 1
    assert published[0]["payload"]["status"]["content"] == "hi"


@pytest.mark.asyncio
async def test_follow_activities_are_not_converted(fake_bus):
    fake_bus.topic("activities").messages = [(1,
                                              "Follow",
                                              "https://local/activities/1",
                                              datetime.now(timezone.utc),
                                              NOTE_PAYLOAD)]

    await mod.rebuild()

    assert len(fake_bus.topic("statuses").published) == 0


@pytest.mark.asyncio
async def test_undo_activities_are_not_converted(fake_bus):
    fake_bus.topic("activities").messages = [(1,
                                              "Undo",
                                              "https://local/activities/1",
                                              datetime.now(timezone.utc),
                                              NOTE_PAYLOAD)]

    await mod.rebuild()

    assert len(fake_bus.topic("statuses").published) == 0

