# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from pytest import fixture
from pytest_asyncio import fixture as async_fixture
from unittest.mock import patch

import asyncio

from .fake_asyncpg import InMemoryDatabase, FakePool


CONFIG = {"backend": "postgresql",
          "schema": "public",
          "host": "",
          "port": "0",
          "database": "",
          "user": "",
          "password": ""}


@fixture
def db():
    return InMemoryDatabase()


@async_fixture
async def bus(db):
    async def _create_fake_pool(*args, **kwargs):
        return FakePool(db)

    with patch("profed.core.message_bus.postgresql.asyncpg.create_pool",
               new=_create_fake_pool):
        from profed.core.message_bus.postgresql import init
        bus = await init(CONFIG)

    return bus


@fixture
def topic(bus):
    return bus.topic("test")
 

@async_fixture
async def drain(topic):
    """Subscribe, collect messages until caught_up, cancel, return messages."""
    async def _drain(**subscribe_kwargs):
        caught_up = asyncio.Event()
        collected = []
 
        async def consume():
            async for msg in topic.subscribe("test",
                                              caught_up=caught_up,
                                              **subscribe_kwargs):
                collected.append(msg)
 
        task = asyncio.create_task(consume())
        await asyncio.wait_for(caught_up.wait(), timeout=2.0)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        return collected
 
    return _drain
