# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from pytest import fixture
from pytest_asyncio import fixture as async_fixture
from unittest.mock import patch

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

