# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import profed.components.incoming_timeline.translator as mod
import profed.components.own_timeline.translator as own_mod
from profed.core.message_bus.source_key import source_key
from profed.identity import status_id


EMITTED_AT = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

NOTE_PAYLOAD = {"username": "alice",
                "activity": {"actor": "https://remote/bob",
                             "object": {"id": "https://remote/notes/1",
                                        "type": "Note",
                                        "url": "https://remote/notes/1",
                                        "published": "2026-01-01T00:00:00.000Z",
                                        "content": "hi"}}}

DELETE_PAYLOAD = {"username": "alice",
                  "activity": {"actor": "https://remote/bob", "object": "https://remote/notes/1"}}


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
async def test_create_publishes_status_content_to_timeline():
    bus, published = _fake_bus()

    with patch.object(mod, "message_bus", return_value=bus):
        await mod._convert("Create", "https://remote/notes/1#create", NOTE_PAYLOAD, EMITTED_AT, 7)

    assert bus.topic.call_args[0][0] == "timeline"
    assert published[0]["payload"]["status_id"] == "https://remote/notes/1"
    assert published[0]["payload"]["status"]["content"] == "hi"


@pytest.mark.asyncio
async def test_create_carries_the_remote_actor_url():
    bus, published = _fake_bus()

    with patch.object(mod, "message_bus", return_value=bus):
        await mod._convert("Create", "https://remote/notes/1#create", NOTE_PAYLOAD, EMITTED_AT, 7)

    assert published[0]["payload"]["actor_url"] == "https://remote/bob"


@pytest.mark.asyncio
async def test_create_marks_the_status_as_incoming():
    bus, published = _fake_bus()

    with patch.object(mod, "message_bus", return_value=bus):
        await mod._convert("Create", "https://remote/notes/1#create", NOTE_PAYLOAD, EMITTED_AT, 42)

    assert published[0]["payload"]["status"]["id"] == status_id(EMITTED_AT, 42, own=False)
    assert int(published[0]["payload"]["status"]["id"]) % 2 == 0


@pytest.mark.asyncio
async def test_create_derives_message_id_from_resolved_activities_sequence():
    bus, published = _fake_bus()

    with patch.object(mod, "message_bus", return_value=bus):
        await mod._convert("Create", "https://remote/notes/1#create", NOTE_PAYLOAD, EMITTED_AT, 42)

    assert published[0]["message_id"] == source_key("resolved_activities").message_id(42)


@pytest.mark.asyncio
async def test_delete_publishes_only_the_status_id():
    bus, published = _fake_bus()

    with patch.object(mod, "message_bus", return_value=bus):
        await mod._convert_delete("Delete", "https://remote/notes/1#delete", DELETE_PAYLOAD, EMITTED_AT, 7)

    assert published[0]["payload"] == {"username": "alice", "status_id": "https://remote/notes/1"}


@pytest.mark.asyncio
async def test_both_sources_never_dedup_against_each_other():
    bus_incoming, incoming = _fake_bus()
    bus_own, own = _fake_bus()

    with patch.object(mod, "message_bus", return_value=bus_incoming):
        await mod._convert("Create", "https://remote/notes/1#create", NOTE_PAYLOAD, EMITTED_AT, 42)
    with patch.object(own_mod, "message_bus", return_value=bus_own):
        await own_mod._forward("Create", "https://local/notes/1", {"username": "alice"}, 42)

    assert incoming[0]["message_id"] != own[0]["message_id"]


@pytest.mark.asyncio
async def test_incoming_and_own_statuses_get_different_ids_at_the_same_time():
    assert status_id(EMITTED_AT, 42, own=False) != status_id(EMITTED_AT, 42, own=True)


@pytest.mark.asyncio
async def test_create_activities_are_converted_on_rebuild(fake_bus):
    fake_bus.topic("resolved_activities").messages = [(1,
                                                       "Create",
                                                       "https://remote/notes/1#create",
                                                       EMITTED_AT,
                                                       NOTE_PAYLOAD)]

    await mod.rebuild()

    published = fake_bus.topic("timeline").published
    assert len(published) == 1
    assert published[0]["payload"]["status"]["content"] == "hi"


@pytest.mark.asyncio
async def test_follow_activities_are_not_converted(fake_bus):
    fake_bus.topic("resolved_activities").messages = [(1,
                                                       "Follow",
                                                       "https://remote/activities/1",
                                                       EMITTED_AT,
                                                       NOTE_PAYLOAD)]

    await mod.rebuild()

    assert len(fake_bus.topic("timeline").published) == 0

