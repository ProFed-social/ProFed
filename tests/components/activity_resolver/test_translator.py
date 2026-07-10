# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, patch
from profed.components.activity_resolver import translator


def _payload(actor="https://remote.example/users/bob", obj=None):
    return {"username": "alice",
            "activity": {"actor": actor,
                         "object": obj if obj is not None
                         else {"id": "https://remote.example/notes/1", "type": "Note"}}}


@pytest.mark.asyncio
async def test_create_resolves_object_and_publishes(fake_bus):
    resolved = {"id": "https://remote.example/notes/1", "type": "Note", "content": "RESOLVED"}

    with patch.object(translator, "resolve_object", AsyncMock(return_value=resolved)) as ro:
        await translator._forwarder(True)("Create", "https://remote.example/act/1", _payload(), 5)

    ro.assert_awaited_once()
    published = fake_bus.topic("resolved_activities").published
    assert len(published) == 1
    assert published[0]["event_type"] == "Create"
    assert published[0]["object_id"] == "https://remote.example/act/1"
    assert published[0]["payload"]["username"] == "alice"
    assert published[0]["payload"]["activity"]["object"] == resolved


@pytest.mark.asyncio
async def test_resolve_uses_actor_host_as_trusted_origin(fake_bus):
    with patch.object(translator, "resolve_object", AsyncMock(return_value={})) as ro:
        await translator._forwarder(True)("Create", "https://remote.example/act/1", _payload(), 5)

    assert ro.await_args.args[1] == "remote.example"


@pytest.mark.asyncio
async def test_delete_passes_through_without_resolving(fake_bus):
    payload = _payload(obj="https://remote.example/notes/1")

    with patch.object(translator, "resolve_object", AsyncMock()) as ro:
        await translator._forwarder(False)("Delete", "https://remote.example/act/2", payload, 6)

    ro.assert_not_called()
    published = fake_bus.topic("resolved_activities").published
    assert published[0]["payload"]["activity"]["object"] == "https://remote.example/notes/1"


@pytest.mark.asyncio
async def test_message_id_is_derived_from_source_sequence(fake_bus):
    with patch.object(translator, "resolve_object", AsyncMock(return_value={})):
        await translator._forwarder(True)("Create", "https://remote.example/act/1", _payload(), 42)

    topic = fake_bus.topic("resolved_activities", lookup_message_ids=True)
    assert await topic.exists(translator._SOURCE.message_id(42))


@pytest.mark.asyncio
async def test_already_resolved_source_event_is_skipped(fake_bus):
    topic = fake_bus.topic("resolved_activities", lookup_message_ids=True)
    async with topic.publish() as publish:
        await publish("Create", "x", {"username": "a", "activity": {}}, message_id=translator._SOURCE.message_id(7))
    before = len(topic.published)

    with patch.object(translator, "resolve_object", AsyncMock()) as ro:
        await translator._forwarder(True)("Create", "https://remote.example/act/1", _payload(), 7)

    ro.assert_not_called()
    assert len(topic.published) == before

