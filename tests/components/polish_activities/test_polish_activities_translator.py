# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import profed.components.polish_activities.translator as mod
from profed import mentions
from profed.core.message_bus.source_key import source_key


PAYLOAD = {"username": "alice",
           "activity": {"actor": "https://local/actors/alice", "object": {"content": "hi @bob"}}}

NOTE_PAYLOAD = {"username": "alice",
                "activity": {"type": "Create",
                             "actor": "https://local/actors/alice",
                             "object": {"type": "Note",
                                        "id": "https://local/notes/1",
                                        "content": "hi @dave@r.io"}}}


async def _fake_lookup(acct):
    return "https://r.io/dave" if acct == "dave@r.io" else None


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
async def test_polish_linkifies_content_and_sets_tag_cc():
    bus, published = _fake_bus()
    with patch.object(mod, "message_bus", return_value=bus), \
         patch.object(mod, "_resolve_one", mentions.resolver(_fake_lookup)):
        await mod._polish_and_forward("Create", "https://local/notes/1", NOTE_PAYLOAD, 7)

    obj = published[0]["payload"]["activity"]["object"]
    assert 'href="https://r.io/dave"' in obj["content"]
    assert ">@dave</a>" in obj["content"]
    assert obj["tag"] == [{"type": "Mention", "href": "https://r.io/dave", "name": "@dave@r.io"}]
    assert obj["cc"] == ["https://r.io/dave"]
    assert published[0]["payload"]["activity"]["cc"] == ["https://r.io/dave"]


@pytest.mark.asyncio
async def test_polish_leaves_unresolved_mention_as_text():
    payload = {"username": "alice",
               "activity": {"type": "Create",
                            "object": {"type": "Note", "content": "hi @ghost@r.io"}}}
    bus, published = _fake_bus()
    with patch.object(mod, "message_bus", return_value=bus), \
         patch.object(mod, "_resolve_one", mentions.resolver(_fake_lookup)):
        await mod._polish_and_forward("Create", "x", payload, 1)

    obj = published[0]["payload"]["activity"]["object"]
    assert obj["content"] == "hi @ghost@r.io"
    assert obj["tag"] == []
    assert obj["cc"] == []
    assert published[0]["payload"]["activity"]["cc"] is None


@pytest.mark.asyncio
async def test_create_is_transformed_via_rebuild(fake_bus):
    fake_bus.topic("raw_activities").messages = [(1, "Create", "https://local/notes/1",
                                                  datetime.now(timezone.utc), NOTE_PAYLOAD)]
    with patch.object(mod, "_resolve_one", mentions.resolver(_fake_lookup)):
        await mod.rebuild()

    obj = fake_bus.topic("activities").published[0]["payload"]["activity"]["object"]
    assert obj["cc"] == ["https://r.io/dave"]


@pytest.mark.asyncio
async def test_non_content_activity_passed_through(fake_bus):
    fake_bus.topic("raw_activities").messages = [(1, "Follow", "https://local/actors/alice#follow",
                                                  datetime.now(timezone.utc), PAYLOAD)]

    await mod.rebuild()

    assert len(fake_bus.topic("activities").published) == 1
    assert fake_bus.topic("activities").published[0]["event_type"] == "Follow"
    assert fake_bus.topic("activities").published[0]["payload"] == PAYLOAD

