# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from profed.components.activity_resolver import translator


EMITTED = datetime(2026, 5, 1, tzinfo=timezone.utc)


def _payload(actor="https://remote.example/users/bob", obj=None):
    return {"username": "alice",
            "activity": {"actor": actor,
                         "object": obj if obj is not None
                         else {"id": "https://remote.example/notes/1", "type": "Note"}}}


@pytest.mark.asyncio
async def test_create_flattens_and_publishes(fake_bus):
    flattened = {"actor": "https://remote.example/users/bob", "object": "https://remote.example/notes/1"}

    with patch.object(translator, "flatten_references", Mock(return_value=flattened)) as flatten:
        await translator._forwarder(True)("Create", "https://remote.example/act/1", _payload(), EMITTED, 5)

    flatten.assert_called_once()
    published = fake_bus.topic("resolved_activities").published
    assert len(published) == 1
    assert published[0]["event_type"] == "Create"
    assert published[0]["object_id"] == "https://remote.example/act/1"
    assert published[0]["payload"]["username"] == "alice"
    assert published[0]["payload"]["activity"] == flattened


@pytest.mark.asyncio
async def test_flatten_receives_the_envelope_and_the_fetcher_enqueue(fake_bus):
    with patch.object(translator, "flatten_references", Mock(return_value={})) as flatten:
        await translator._forwarder(True)("Create", "https://remote.example/act/1", _payload(), EMITTED, 5)

    _, object_id, event_type, emitted_at, _, enqueue = flatten.call_args.args
    assert object_id == "https://remote.example/act/1"
    assert event_type == "Create"
    assert emitted_at == EMITTED
    assert enqueue is translator.fetcher.enqueue


@pytest.mark.asyncio
async def test_delete_passes_through_without_flattening(fake_bus):
    payload = _payload(obj="https://remote.example/notes/1")

    with patch.object(translator, "flatten_references", Mock()) as flatten:
        await translator._forwarder(False)("Delete", "https://remote.example/act/2", payload, EMITTED, 6)

    flatten.assert_not_called()
    published = fake_bus.topic("resolved_activities").published
    assert published[0]["payload"]["activity"]["object"] == "https://remote.example/notes/1"


@pytest.mark.asyncio
async def test_message_id_is_derived_from_source_sequence(fake_bus):
    with patch.object(translator, "flatten_references", Mock(return_value={})):
        await translator._forwarder(True)("Create", "https://remote.example/act/1", _payload(), EMITTED, 42)

    topic = fake_bus.topic("resolved_activities", lookup_message_ids=True)
    assert await topic.exists(translator._SOURCE.message_id(42))


@pytest.mark.asyncio
async def test_already_resolved_source_event_is_skipped(fake_bus):
    topic = fake_bus.topic("resolved_activities", lookup_message_ids=True)
    async with topic.publish() as publish:
        await publish("Create", "x", {"username": "a", "activity": {}}, message_id=translator._SOURCE.message_id(7))
    before = len(topic.published)

    with patch.object(translator, "flatten_references", Mock()) as flatten:
        await translator._forwarder(True)("Create", "https://remote.example/act/1", _payload(), EMITTED, 7)

    flatten.assert_not_called()
    assert len(topic.published) == before

