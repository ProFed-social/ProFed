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
    subscriber = topic.subscribe("test", caught_up=caught_up)

    first  = await subscriber.__anext__()
    second = await subscriber.__anext__()

    assert first["v"] == "a"
    assert second["v"] == "b"
    await asyncio.sleep(0.1)
    assert caught_up.is_set()


@pytest.mark.asyncio
async def test_caught_up_not_set_before_messages_delivered(topic, db):
    db.insert_message("public.test", {"v": "a"})

    caught_up = asyncio.Event()
    subscriber = topic.subscribe("test", caught_up=caught_up)

    assert not caught_up.is_set()

    await subscriber.__anext__()
    await asyncio.sleep(0.1)

    assert caught_up.is_set()


@pytest.mark.asyncio
async def test_caught_up_set_only_once(topic, db):
    db.insert_message("public.test", {"v": "a"})

    caught_up = asyncio.Event()
    subscriber = topic.subscribe("test", caught_up=caught_up)

    await subscriber.__anext__()
    await asyncio.sleep(0.1)
    assert caught_up.is_set()

    caught_up.clear()
    db.insert_message("public.test", {"v": "b"})

    second = await subscriber.__anext__()
    assert second["v"] == "b"
    assert not caught_up.is_set()


@pytest.mark.asyncio
async def test_no_caught_up_argument_does_not_raise(topic, db):
    db.insert_message("public.test", {"v": "a"})
    subscriber = topic.subscribe("test")
    msg = await subscriber.__anext__()
    assert msg["v"] == "a"
