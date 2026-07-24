# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import profed.components.own_timeline.translator as mod
from profed.core.message_bus.source_key import source_key


PAYLOAD = {"username": "alice",
           "status_id": "https://local/notes/1",
           "actor_url": "https://local/actors/alice",
           "status": {"id": "42", "content": "<p>hi</p>"}}


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


def _messages(verb):
    return [(1, verb, "https://local/notes/1", datetime.now(timezone.utc), PAYLOAD)]


@pytest.mark.asyncio
async def test_forward_publishes_to_timeline_unchanged():
    bus, published = _fake_bus()
    with patch.object(mod, "message_bus", return_value=bus):
        await mod._forward("Create", "https://local/notes/1", PAYLOAD, 7)

    assert bus.topic.call_args[0][0] == "timeline"
    assert len(published) == 1
    assert published[0]["event_type"] == "Create"
    assert published[0]["object_id"] == "https://local/notes/1"
    assert published[0]["payload"] == PAYLOAD


@pytest.mark.asyncio
async def test_forward_derives_message_id_from_statuses_sequence():
    bus, published = _fake_bus()
    with patch.object(mod, "message_bus", return_value=bus):
        await mod._forward("Update", "https://local/notes/1", PAYLOAD, 42)

    assert published[0]["message_id"] == source_key("statuses").message_id(42)


@pytest.mark.asyncio
async def test_create_statuses_passed_through(fake_bus):
    fake_bus.topic("statuses").messages = _messages("Create")

    await mod.rebuild()

    assert len(fake_bus.topic("timeline").published) == 1
    assert fake_bus.topic("timeline").published[0]["event_type"] == "Create"


@pytest.mark.asyncio
async def test_update_statuses_passed_through(fake_bus):
    fake_bus.topic("statuses").messages = _messages("Update")

    await mod.rebuild()

    assert fake_bus.topic("timeline").published[0]["event_type"] == "Update"


@pytest.mark.asyncio
async def test_delete_statuses_passed_through(fake_bus):
    fake_bus.topic("statuses").messages = _messages("Delete")

    await mod.rebuild()

    assert fake_bus.topic("timeline").published[0]["event_type"] == "Delete"


@pytest.mark.asyncio
async def test_announce_statuses_passed_through(fake_bus):
    fake_bus.topic("statuses").messages = _messages("Announce")

    await mod.rebuild()

    assert fake_bus.topic("timeline").published[0]["event_type"] == "Announce"


@pytest.mark.asyncio
async def test_the_status_content_is_forwarded_unchanged(fake_bus):
    fake_bus.topic("statuses").messages = _messages("Create")

    await mod.rebuild()

    assert fake_bus.topic("timeline").published[0]["payload"] == PAYLOAD

