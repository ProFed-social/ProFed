# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from profed.core.message_bus.source_key import source_key


@pytest.mark.asyncio
async def test_plain_topic_has_no_exists(bus):
    assert not hasattr(bus.topic("test"), "exists")


@pytest.mark.asyncio
async def test_lookup_topic_has_exists(bus):
    assert hasattr(bus.topic("test", lookup_message_ids=True), "exists")


@pytest.mark.asyncio
async def test_exists_returns_true_for_published_message_id(bus):
    topic = bus.topic("test", lookup_message_ids=True)
    key = source_key("users").message_id(1)

    async with topic.publish() as publish:
        await publish("created", "o1", {"x": 1}, message_id=key)

    assert await topic.exists(key) is True


@pytest.mark.asyncio
async def test_exists_returns_false_for_unknown_message_id(bus):
    topic = bus.topic("test", lookup_message_ids=True)

    async with topic.publish() as publish:
        await publish("created", "o1", {"x": 1}, message_id=source_key("users").message_id(1))

    assert await topic.exists(source_key("users").message_id(2)) is False

