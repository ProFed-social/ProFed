# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from pytest import fixture
from pytest_asyncio import fixture as async_fixture
from unittest.mock import patch

import asyncio
import logging
import os

from .fake_asyncpg import InMemoryDatabase, FakePool
from profed.core.message_bus.postgresql import subscriber


CONFIG = {"backend": "postgresql",
          "schema": "public",
          "host": "",
          "port": "0",
          "database": "",
          "user": "",
          "password": "",
          "pool_min_size": 1,
          "pool_max_size": 1}


@fixture
def db():
    return InMemoryDatabase()


@fixture(autouse=True)
def no_process_exit():
    def raise_instead(*args):
        raise RuntimeError("corruption")

    with patch.object(os, "_exit", raise_instead), patch.object(logging, "shutdown", lambda: None):
        yield


@async_fixture
async def bus(db):
    async def _create_fake_pool(*args, **kwargs):
        return FakePool(db)

    import profed.core.persistence.db_connections as _db
    with patch("profed.core.persistence.db_connections.asyncpg.create_pool",
               new=_create_fake_pool):
        from profed.core.message_bus.postgresql import init
        bus = await init(CONFIG, ["test"])
    _db._pools.clear()

    return bus

@fixture
def topic(bus):
    return bus.topic("test")


@async_fixture
async def drain(topic):
    async def _drain(**subscribe_kwargs):
        caught_up = asyncio.Event()
        collected = []

        async def consume():
            async for msg in topic.subscribe(caught_up=caught_up, **subscribe_kwargs):
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

