# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import pytest
from profed.core.message_bus.postgresql.notifications import _make_notifier


class FakeConnection:
    def __init__(self):
        self.channels: dict = {}
        self.closed = False

    def is_closed(self):
        return self.closed

    async def add_listener(self, channel, callback):
        self.channels.setdefault(channel, []).append(callback)

    async def remove_listener(self, channel, callback):
        self.channels.get(channel, []).remove(callback)

    def deliver(self, channel):
        for callback in self.channels.get(channel, []):
            callback(self, 0, channel, "")


class FakePool:
    def __init__(self):
        self.connections = []

    def acquire(self):
        pool = self

        class _Ctx:
            def __await__(self):
                async def _acquire():
                    conn = FakeConnection()
                    pool.connections.append(conn)
                    return conn
                return _acquire().__await__()

        return _Ctx()


@pytest.mark.asyncio
async def test_the_first_listener_opens_one_connection():
    listen, _, _ = _make_notifier()
    pool = FakePool()

    await listen(pool, "topic_a", asyncio.Event())

    assert len(pool.connections) == 1


@pytest.mark.asyncio
async def test_many_listeners_share_one_connection():
    listen, _, _ = _make_notifier()
    pool = FakePool()

    for name in ("topic_a", "topic_b", "topic_c"):
        await listen(pool, name, asyncio.Event())

    assert len(pool.connections) == 1


@pytest.mark.asyncio
async def test_a_channel_is_registered_once_per_topic():
    listen, _, _ = _make_notifier()
    pool = FakePool()

    await listen(pool, "topic_a", asyncio.Event())
    await listen(pool, "topic_a", asyncio.Event())

    assert len(pool.connections[0].channels["topic_a"]) == 1


@pytest.mark.asyncio
async def test_a_notification_wakes_every_listener_of_its_channel():
    listen, _, _ = _make_notifier()
    pool = FakePool()
    first, second = asyncio.Event(), asyncio.Event()
    await listen(pool, "topic_a", first)
    await listen(pool, "topic_a", second)

    pool.connections[0].deliver("topic_a")

    assert first.is_set() and second.is_set()


@pytest.mark.asyncio
async def test_a_notification_leaves_other_channels_alone():
    listen, _, _ = _make_notifier()
    pool = FakePool()
    listener_a, listener_b = asyncio.Event(), asyncio.Event()
    await listen(pool, "topic_a", listener_a)
    await listen(pool, "topic_b", listener_b)

    pool.connections[0].deliver("topic_a")

    assert listener_a.is_set()
    assert not listener_b.is_set()


@pytest.mark.asyncio
async def test_the_last_listener_of_a_channel_stops_listening():
    listen, forget, _ = _make_notifier()
    pool = FakePool()
    event = asyncio.Event()
    await listen(pool, "topic_a", event)

    await forget("topic_a", event)

    assert pool.connections[0].channels["topic_a"] == []


@pytest.mark.asyncio
async def test_a_remaining_listener_keeps_the_channel():
    listen, forget, _ = _make_notifier()
    pool = FakePool()
    first, second = asyncio.Event(), asyncio.Event()
    await listen(pool, "topic_a", first)
    await listen(pool, "topic_a", second)

    await forget("topic_a", first)

    assert len(pool.connections[0].channels["topic_a"]) == 1


@pytest.mark.asyncio
async def test_forgetting_an_unknown_listener_is_harmless():
    _, forget, _ = _make_notifier()

    await forget("topic_a", asyncio.Event())


@pytest.mark.asyncio
async def test_a_closed_connection_is_replaced():
    listen, _, _ = _make_notifier()
    pool = FakePool()
    await listen(pool, "topic_a", asyncio.Event())
    pool.connections[0].closed = True

    await listen(pool, "topic_b", asyncio.Event())

    assert len(pool.connections) == 2


@pytest.mark.asyncio
async def test_a_replaced_connection_listens_to_every_channel_again():
    listen, _, _ = _make_notifier()
    pool = FakePool()
    await listen(pool, "topic_a", asyncio.Event())
    await listen(pool, "topic_b", asyncio.Event())
    pool.connections[0].closed = True

    await listen(pool, "topic_c", asyncio.Event())

    assert sorted(pool.connections[1].channels) == ["topic_a", "topic_b", "topic_c"]


@pytest.mark.asyncio
async def test_the_listener_count_reports_every_waiting_subscriber():
    listen, forget, listener_count = _make_notifier()
    pool = FakePool()
    first, second = asyncio.Event(), asyncio.Event()
    await listen(pool, "topic_a", first)
    await listen(pool, "topic_b", second)

    assert listener_count() == 2

    await forget("topic_a", first)

    assert listener_count() == 1

