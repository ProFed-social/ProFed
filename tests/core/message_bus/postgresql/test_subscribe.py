# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from tests.core.message_bus.postgresql import fake_asyncpg


@pytest.mark.asyncio
async def test_messages_are_yielded_in_order(topic, db):

    db.insert_message("public.test", {"v": "a"})
    db.insert_message("public.test", {"v": "b"})
    db.insert_message("public.test", {"v": "c"})

    subscriber = topic.subscribe()

    messages = [
        await subscriber.__anext__(),
        await subscriber.__anext__(),
        await subscriber.__anext__(),
    ]

    assert [m[4]["v"] for m in messages] == ["a", "b", "c"]


@pytest.mark.asyncio
async def test_existing_messages_delivered_without_notify(topic, db, drain):
    db.insert_message("public.test", {"v": "a"})
    db.insert_message("public.test", {"v": "b"})

    messages = await drain()

    assert [m[4]["v"] for m in messages] == ["a", "b"]


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

        assert messages[0][4]["v"] == "a"
        assert len(add_listener_calls) == 1
    finally:
        fake_asyncpg.FakeConnection.add_listener = original_add_listener



@pytest.mark.asyncio
async def test_reconnects_after_a_dropped_connection(topic, db, monkeypatch):
    db.insert_message("public.test", {"v": "a"})
    dropped = []
    real_fetch = fake_asyncpg.FakeConnection.fetch

    async def flaky_fetch(self, query, *args):
        if "ORDER BY id" in query and not dropped:
            dropped.append(True)
            raise OSError("connection dropped")
        return await real_fetch(self, query, *args)

    monkeypatch.setattr(fake_asyncpg.FakeConnection, "fetch", flaky_fetch)

    subscriber = topic.subscribe()
    message = await subscriber.__anext__()
    assert message[4]["v"] == "a"


