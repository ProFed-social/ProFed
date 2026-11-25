# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import pytest
from unittest.mock import patch
from profed.core.frozen import FrozenDict
from tests.core.message_bus.postgresql import fake_asyncpg
from .conftest import CONFIG
from .fake_asyncpg import FakePool


async def _bus_with(db, **overrides):
    async def _create_fake_pool(*args, **kwargs):
        return FakePool(db)

    import profed.core.persistence.db_connections as connections
    with patch("profed.core.persistence.db_connections.asyncpg.create_pool",
               new=_create_fake_pool):
        from profed.core.message_bus.postgresql import init
        bus = await init({**CONFIG, **overrides}, ["test"])
    connections._pools.clear()

    return bus


async def _listening(topic, count):
    events = [asyncio.Event() for _ in range(count)]
    collected: list[list] = [[] for _ in range(count)]

    async def consume(generator, into):
        async for row in generator:
            into.append(row)

    tasks = [asyncio.create_task(consume(topic.subscribe(caught_up=event), into))
             for event, into in zip(events, collected)]
    for event in events:
        await asyncio.wait_for(event.wait(), timeout=2.0)

    return tasks, collected


async def _stopped(tasks):
    for task in tasks:
        task.cancel()
    for task in tasks:
        try:
            await task
        except asyncio.CancelledError:
            pass


async def _until(done, limit=200):
    for _ in range(limit):
        if done():
            return
        await asyncio.sleep(0.01)


def _counting_fetch(reads):
    original = fake_asyncpg.FakeConnection.fetch

    async def counting(self, query, *args):
        rows = await original(self, query, *args)
        if "ORDER BY id" in query:
            reads.append(len(rows))
        return rows

    return original, counting


@pytest.mark.asyncio
async def test_many_subscribers_of_one_topic_share_a_single_read(topic):
    tasks, collected = await _listening(topic, 3)
    reads: list[int] = []
    original, counting = _counting_fetch(reads)
    fake_asyncpg.FakeConnection.fetch = counting

    try:
        async with topic.publish() as publish:
            await publish("created", "o1", {"v": "a"})
        await _until(lambda: all(group for group in collected))
    finally:
        fake_asyncpg.FakeConnection.fetch = original
        await _stopped(tasks)

    assert [group[-1][4]["v"] for group in collected] == ["a", "a", "a"]
    assert len([size for size in reads if size]) == 1


@pytest.mark.asyncio
async def test_every_subscriber_gets_the_very_same_row(topic):
    tasks, collected = await _listening(topic, 3)

    try:
        async with topic.publish() as publish:
            await publish("created", "o1", {"v": "a"})
        await _until(lambda: all(group for group in collected))
    finally:
        await _stopped(tasks)

    first, second, third = (group[-1] for group in collected)

    assert first[4] is second[4]
    assert second[4] is third[4]


@pytest.mark.asyncio
async def test_one_listen_serves_every_subscriber_of_a_topic(topic):
    channels = []
    original = fake_asyncpg.FakeConnection.add_listener

    async def tracking(self, channel, callback):
        channels.append(channel)
        await original(self, channel, callback)

    fake_asyncpg.FakeConnection.add_listener = tracking
    tasks = []
    try:
        tasks, _ = await _listening(topic, 4)
        await asyncio.sleep(0.05)
    finally:
        fake_asyncpg.FakeConnection.add_listener = original
        await _stopped(tasks)

    assert channels == ["public_test"]


@pytest.mark.asyncio
async def test_the_payload_a_subscriber_gets_cannot_be_changed(topic, db):
    db.insert_message("public.test", {"v": "a", "nested": {"x": 1}})

    payload = (await topic.subscribe().__anext__())[4]

    assert isinstance(payload, FrozenDict)
    with pytest.raises(TypeError):
        payload["v"] = "b"
    with pytest.raises(TypeError):
        payload["nested"]["x"] = 2


@pytest.mark.asyncio
async def test_a_subscriber_starting_at_the_head_reads_no_history(topic, db):
    for value in range(5):
        db.insert_message("public.test", {"v": value})
    reads: list[int] = []
    original, counting = _counting_fetch(reads)
    fake_asyncpg.FakeConnection.fetch = counting

    try:
        caught_up = asyncio.Event()
        task = asyncio.create_task(topic.subscribe(last_seen=5, caught_up=caught_up).__anext__())
        await asyncio.wait_for(caught_up.wait(), timeout=2.0)
        await _stopped([task])
    finally:
        fake_asyncpg.FakeConnection.fetch = original

    assert sum(reads) == 0


@pytest.mark.asyncio
async def test_a_subscriber_that_overflows_its_queue_reads_for_itself(db):
    bus = await _bus_with(db, subscriber_queue=2)
    topic = bus.topic("test")
    caught_up = asyncio.Event()
    seen = []

    async def consume():
        async for row in topic.subscribe(caught_up=caught_up):
            seen.append(row[4]["v"])
            await asyncio.sleep(0)

    task = asyncio.create_task(consume())
    await asyncio.wait_for(caught_up.wait(), timeout=2.0)

    async with topic.publish() as publish:
        for value in range(20):
            await publish("created", f"o{value}", {"v": value})
    await _until(lambda: len(seen) == 20)
    await _stopped([task])

    assert seen == list(range(20))


@pytest.mark.asyncio
async def test_listening_again_with_the_same_event_does_not_register_twice(topic, db):
    from profed.core.message_bus.postgresql import notifications
    channels = []
    original = fake_asyncpg.FakeConnection.add_listener

    async def tracking(self, channel, callback):
        channels.append(channel)
        await original(self, channel, callback)

    fake_asyncpg.FakeConnection.add_listener = tracking
    event = asyncio.Event()
    pool = FakePool(db)
    try:
        await notifications.listen(pool, "public_once", event)
        await notifications.listen(pool, "public_once", event)
        await notifications.listen(pool, "public_once", event)
    finally:
        fake_asyncpg.FakeConnection.add_listener = original
        await notifications.forget("public_once", event)

    assert channels.count("public_once") == 1

