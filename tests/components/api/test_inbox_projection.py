# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock

from profed.core import message_bus

from profed.components.api.storage import inbox_users as storage
from profed.components.api.projections.inbox import rebuild, reset_last_seen


class FakeTopic:
    def __init__(self):
        self.last_seen = 0
        self.snapshots = []
        self.messages = []

    async def last_snapshot(self):
        return self.snapshots[-1] if len(self.snapshots) > 0 else (0, [])

    def subscribe(self, subscriber:str, last_seen: int = 0):
        async def generator():
            for message in self.messages:
                if message[0] > last_seen:
                    self.last_seen = message[0]
                    yield message[1]
        return generator()


class FakeMessageBus:
    def __init__(self):
        self._topics = {}

    def topic(self, name: str):
        if name not in self._topics:
            self._topics[name] = FakeTopic()
        return self._topics[name]


@pytest.fixture
def fake_message_bus():
    backup = message_bus._instance
    message_bus._instance = FakeMessageBus()
    reset_last_seen(0)

    yield message_bus._instance

    message_bus._instance = backup


@pytest.fixture
def fake_storage():
    instance = AsyncMock()
    instance.add = AsyncMock()
    instance.delete = AsyncMock()
    instance.exists = AsyncMock()
    instance.ensure_table = AsyncMock()

    storage.overwrite(instance)

    return instance


@pytest.mark.asyncio
async def test_rebuild_success(fake_message_bus, fake_storage):
    fake_message_bus.topic("users").snapshots = [
                (42, [{"username": "alice"}])
            ]
    await rebuild()
    fake_storage.add.assert_awaited_once_with("alice")


@pytest.mark.asyncio
async def test_rebuild_no_snapshot(fake_message_bus, fake_storage):
    fake_message_bus.topic("users").snapshots = [(None, [])]
    await rebuild()
    fake_storage.add.assert_not_awaited()


@pytest.mark.asyncio
async def test_rebuild_add_failure(fake_message_bus, fake_storage):
    fake_message_bus.topic("users").snapshots = [
                (42, [{"username": "alice"}])
            ]
    fake_storage.add.side_effect = RuntimeError("DB error")

    with pytest.raises(RuntimeError, match="DB error"):
        await rebuild()


@pytest.mark.asyncio
async def test_projection_multiple_users(fake_message_bus, fake_storage):
    fake_message_bus.topic("users").snapshots = [
                (10, [{"username": "alice"},
                      {"username": "bob"}])
            ]
    await rebuild()
    assert fake_storage.add.await_count == 2


@pytest.mark.asyncio
async def test_projection_invalid_payload(fake_message_bus, fake_storage):
    fake_message_bus.topic("users").snapshots = [
            (5, [{"no_username": "alice"}])
            ]
    await rebuild()
    assert fake_storage.add.await_count == 0


@pytest.mark.asyncio
async def test_projection_multiple_users_some_malformed(fake_message_bus, fake_storage):
    fake_message_bus.topic("users").snapshots = [
            (10,
             [{"username": "alice"},
              {"username": ""},
              {"no_username": "alice"},
              {"username": "bob"}])
            ]
    await rebuild()
    assert fake_storage.add.await_count == 2

