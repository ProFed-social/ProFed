# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import pytest


@pytest.mark.asyncio
async def test_caught_up_set_when_no_messages_exist(topic, db):
    caught_up = asyncio.Event()
    subscriber = topic.subscribe("test", caught_up=caught_up)

    first = asyncio.create_task(subscriber.__anext__())
    await asyncio.sleep(0.1)

    assert caught_up.is_set()
    first.cancel()


@pytest.mark.asyncio
async def test_caught_up_set_after_existing_messages_delivered(topic, db):
    db.insert_message("public.test", {"v": "a"})
    db.insert_message("public.test", {"v": "b"})

    caught_up = asyncio.Event()

    messages = []
    async def consume():
        async for msg in topic.subscribe("test", caught_up=caught_up):
            messages.append(msg)
    task = asyncio.create_task(consume())
    await asyncio.wait_for(caught_up.wait(), timeout=2.0)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    assert [m["v"] for m in messages] == ["a", "b"]
    assert caught_up.is_set()


@pytest.mark.asyncio
async def test_caught_up_not_set_before_messages_delivered(topic, db):
    db.insert_message("public.test", {"v": "a"})

    caught_up = asyncio.Event()
    assert not caught_up.is_set()

    messages = []
    async def consume():
        async for msg in topic.subscribe("test", caught_up=caught_up):
            messages.append(msg)
    task = asyncio.create_task(consume())
    await asyncio.wait_for(caught_up.wait(), timeout=2.0)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    assert messages[0]["v"] == "a"
    assert caught_up.is_set()


@pytest.mark.asyncio
async def test_caught_up_set_only_once(topic, db):
    caught_up = asyncio.Event()
    # Start with empty topic: caught_up fires on the first idle loop
    async def consume():
        async for _ in topic.subscribe("test", caught_up=caught_up):
            pass
    task = asyncio.create_task(consume())
    await asyncio.wait_for(caught_up.wait(), timeout=2.0)
    assert caught_up.is_set()
    # Clear and let the subscriber loop at least once more (min_wait = 0.05 s)
    caught_up.clear()
    await asyncio.sleep(0.2)
    # backlog_done=True prevents a second caught_up.set()
    assert not caught_up.is_set()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_no_caught_up_argument_does_not_raise(topic, db):
    db.insert_message("public.test", {"v": "a"})
    subscriber = topic.subscribe("test")
    msg = await subscriber.__anext__()
    assert msg["v"] == "a"
