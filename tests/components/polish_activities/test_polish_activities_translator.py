# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import profed.components.polish_activities.translator as mod
from profed.core.message_bus.source_key import source_key


PAYLOAD = {"username": "alice",
           "activity": {"actor": "https://local/actors/alice", "object": {"content": "hi @bob"}}}


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
async def test_forward_publishes_to_activities_unchanged():
    bus, published = _fake_bus()
    with patch.object(mod, "message_bus", return_value=bus):
        await mod._forward("Create", "https://local/notes/1", PAYLOAD, 7)

    assert bus.topic.call_args[0][0] == "activities"
    assert len(published) == 1
    assert published[0]["event_type"] == "Create"
    assert published[0]["object_id"] == "https://local/notes/1"
    assert published[0]["payload"] == PAYLOAD


@pytest.mark.asyncio
async def test_forward_derives_message_id_from_raw_activities_sequence():
    bus, published = _fake_bus()
    with patch.object(mod, "message_bus", return_value=bus):
        await mod._forward("Update", "https://local/notes/1", PAYLOAD, 42)

    assert published[0]["message_id"] == source_key("raw_activities").message_id(42)


@pytest.mark.asyncio
async def test_create_activity_passed_through_to_activities(fake_bus):
    fake_bus.topic("raw_activities").messages = [(1, "Create", "https://local/notes/1",
                                                  datetime.now(timezone.utc), PAYLOAD)]

    await mod.rebuild()

    assert len(fake_bus.topic("activities").published) == 1
    assert fake_bus.topic("activities").published[0]["event_type"] == "Create"
    assert fake_bus.topic("activities").published[0]["payload"] == PAYLOAD


@pytest.mark.asyncio
async def test_non_note_activity_passed_through_to_activities(fake_bus):
    fake_bus.topic("raw_activities").messages = [(1, "Follow", "https://local/actors/alice#follow",
                                                  datetime.now(timezone.utc), PAYLOAD)]

    await mod.rebuild()

    assert len(fake_bus.topic("activities").published) == 1
    assert fake_bus.topic("activities").published[0]["event_type"] == "Follow"

