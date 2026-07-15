# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import profed.components.incoming_timeline.translator as mod
import profed.components.own_timeline.translator as own_mod
from profed.core.message_bus.source_key import source_key


PAYLOAD = {"username": "alice",
           "activity": {"actor": "https://remote/bob", "object": {"content": "hi"}}}


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
async def test_forward_publishes_to_timeline_unchanged():
    bus, published = _fake_bus()
    with patch.object(mod, "message_bus", return_value=bus):
        await mod._forward("Create", "https://remote/notes/1", PAYLOAD, 3)

    assert bus.topic.call_args[0][0] == "timeline"
    assert published[0]["event_type"] == "Create"
    assert published[0]["object_id"] == "https://remote/notes/1"
    assert published[0]["payload"] == PAYLOAD


@pytest.mark.asyncio
async def test_forward_derives_message_id_from_resolved_activities_sequence():
    bus, published = _fake_bus()
    with patch.object(mod, "message_bus", return_value=bus):
        await mod._forward("Delete", "https://remote/notes/1", PAYLOAD, 42)

    assert published[0]["message_id"] == source_key("resolved_activities").message_id(42)


@pytest.mark.asyncio
async def test_both_sources_never_dedup_against_each_other():
    own_bus, own_published = _fake_bus()
    incoming_bus, incoming_published = _fake_bus()

    with patch.object(own_mod, "message_bus", return_value=own_bus):
        await own_mod._forward("Create", "https://x/notes/1", PAYLOAD, 5)
    with patch.object(mod, "message_bus", return_value=incoming_bus):
        await mod._forward("Create", "https://x/notes/1", PAYLOAD, 5)

    assert own_published[0]["message_id"] != incoming_published[0]["message_id"]


@pytest.mark.asyncio

async def test_create_activities_passed_through(fake_bus):
    fake_bus.topic("resolved_activities").messages = [(1, "Create", "https://remote/notes/1",
                                                       datetime.now(timezone.utc), PAYLOAD)]

    await mod.rebuild()


    assert len(fake_bus.topic("timeline").published) == 1
    assert fake_bus.topic("timeline").published[0]["event_type"] == "Create"
@pytest.mark.asyncio
async def test_update_activities_passed_through(fake_bus):
    fake_bus.topic("resolved_activities").messages = [(1, "Update", "https://remote/notes/1",
                                                       datetime.now(timezone.utc), PAYLOAD)]
    await mod.rebuild()
    assert len(fake_bus.topic("timeline").published) == 1
    assert fake_bus.topic("timeline").published[0]["event_type"] == "Update"
@pytest.mark.asyncio
async def test_delete_activities_passed_through(fake_bus):
    fake_bus.topic("resolved_activities").messages = [(1, "Delete", "https://remote/notes/1",
                                                       datetime.now(timezone.utc), PAYLOAD)]
    await mod.rebuild()
    assert len(fake_bus.topic("timeline").published) == 1
    assert fake_bus.topic("timeline").published[0]["event_type"] == "Delete"
@pytest.mark.asyncio
async def test_announce_activities_passed_through(fake_bus):
    fake_bus.topic("resolved_activities").messages = [(1, "Announce", "https://remote/notes/1",
                                                       datetime.now(timezone.utc), PAYLOAD)]
    await mod.rebuild()
    assert len(fake_bus.topic("timeline").published) == 1
    assert fake_bus.topic("timeline").published[0]["event_type"] == "Announce"
@pytest.mark.asyncio
async def test_follow_activities_not_passed_through(fake_bus):
    fake_bus.topic("resolved_activities").messages = [(1, "Follow", "https://remote/activities/1",
                                                       datetime.now(timezone.utc), PAYLOAD)]
    await mod.rebuild()
    assert len(fake_bus.topic("timeline").published) == 0
@pytest.mark.asyncio
async def test_accept_activities_not_passed_through(fake_bus):
    fake_bus.topic("resolved_activities").messages = [(1, "Accept", "https://remote/activities/1",
                                                       datetime.now(timezone.utc), PAYLOAD)]
    await mod.rebuild()
    assert len(fake_bus.topic("timeline").published) == 0
@pytest.mark.asyncio
async def test_reject_activities_not_passed_through(fake_bus):
    fake_bus.topic("resolved_activities").messages = [(1, "Reject", "https://remote/activities/1",
                                                       datetime.now(timezone.utc), PAYLOAD)]
    await mod.rebuild()
    assert len(fake_bus.topic("timeline").published) == 0
@pytest.mark.asyncio
async def test_undo_activities_not_passed_through(fake_bus):
    fake_bus.topic("resolved_activities").messages = [(1, "Undo", "https://remote/activities/1",
                                                       datetime.now(timezone.utc), PAYLOAD)]
    await mod.rebuild()
    assert len(fake_bus.topic("timeline").published) == 0
@pytest.mark.asyncio
async def test_like_activities_not_passed_through(fake_bus):
    fake_bus.topic("resolved_activities").messages = [(1, "Like", "https://remote/activities/1",
                                                       datetime.now(timezone.utc), PAYLOAD)]
    await mod.rebuild()
    assert len(fake_bus.topic("timeline").published) == 0
@pytest.mark.asyncio
async def test_block_activities_not_passed_through(fake_bus):
    fake_bus.topic("resolved_activities").messages = [(1, "Block", "https://remote/activities/1",
                                                       datetime.now(timezone.utc), PAYLOAD)]
    await mod.rebuild()
    assert len(fake_bus.topic("timeline").published) == 0

