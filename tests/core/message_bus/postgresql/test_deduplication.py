# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import pytest
from profed.core.message_bus.source_key import source_key

@pytest.mark.asyncio
async def test_subscribe_with_sequence_id_yields_id_and_message(topic, db):
    db.insert_message("public.test", {"v": "a"}, i=7)

    subscriber = topic.subscribe(include_sequence_id=True)

    sequence_id, message = await subscriber.__anext__()

    assert sequence_id == 7
    assert message == {"v": "a"}


@pytest.mark.asyncio
async def test_publish_with_dedupe_key_inserts_once(topic, db):
    key = source_key("users").message_id(1)

    async with topic.publish() as publish:
        first = await publish({"x": 1}, message_id=key)
        second = await publish({"x": 1}, message_id=key)

    assert first is 1
    assert second is None
    assert len(db.messages["public.test"]) == 1


@pytest.mark.asyncio
async def test_publish_with_different_dedupe_keys_inserts_both(topic, db):
    key1 = source_key("users").message_id(1)
    key2 = source_key("users").message_id(2)

    async with topic.publish() as publish:
        assert await publish({"x": 1}, message_id=key1) is 1 
        assert await publish({"x": 2}, message_id=key2) is 2

    assert len(db.messages["public.test"]) == 2


@pytest.mark.asyncio
async def test_subscribe_with_message_id_sees_only_one_deduplicated_message(topic, db):
    key = source_key("users").message_id(1)

    async with topic.publish() as publish:
        await publish({"x": 1}, message_id=key)
        await publish({"x": 1}, message_id=key)

    subscriber = topic.subscribe(include_sequence_id=True)
    sequence_id, message = await subscriber.__anext__()

    assert sequence_id == 1
    assert message == {"x": 1}

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(subscriber.__anext__(), timeout=0.05)

