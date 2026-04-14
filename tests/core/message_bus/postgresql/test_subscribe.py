# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
import asyncio
from tests.core.message_bus.postgresql import fake_asyncpg


@pytest.mark.asyncio
async def test_messages_are_yielded_in_order(topic, db):

    db.insert_message("public.test", {"v": "a"})
    db.insert_message("public.test", {"v": "b"})
    db.insert_message("public.test", {"v": "c"})

    subscriber = topic.subscribe("test")

    messages = [
        await subscriber.__anext__(),
        await subscriber.__anext__(),
        await subscriber.__anext__(),
    ]

    assert [m["v"] for m in messages] == ["a", "b", "c"]


@pytest.mark.asyncio
async def test_existing_messages_delivered_without_notify(topic, db, drain):
    db.insert_message("public.test", {"v": "a"})
    db.insert_message("public.test", {"v": "b"})
    messages = await drain()
    assert [m["v"] for m in messages] == ["a", "b"]


@pytest.mark.asyncio
async def test_listeners_registered_only_after_backlog_drained(topic, db, drain):
    db.insert_message("public.test", {"v": "a"})
    add_listener_calls = []
    original_add_listener = fake_asyncpg.FakeConnection.add_listener
    async def tracking_add_listener(self, channel, callback):
        add_listener_calls.append(channel)
        await original_add_listener(self, channel, callback)
    fake_asyncpg.FakeConnection.add_listener = tracking_add_listener
    try:
        messages = await drain()
        assert messages[0]["v"] == "a"
        assert len(add_listener_calls) == 2  # topic + snapshot channel
    finally:
        fake_asyncpg.FakeConnection.add_listener = original_add_listener

