# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from functools import wraps
from unittest.mock import AsyncMock, Mock
from profed.core import message_bus
from profed.components.api.s2s.actor import storage
from profed.components.api.s2s.actor import projection


class FakeTopic:
    def __init__(self):
        self.last_seen = 0
        self.snapshots = []
        self.messages = []

    async def last_snapshot(self):
        return self.snapshots[-1] if len(self.snapshots) > 0 else (0, [])

    def subscribe(self,
                  subscriber:str,
                  last_seen: int = 0,
                  include_sequence_id: bool = False,
                  caught_up=None):
        async def generator():
            for message in self.messages:
                if message[0] > last_seen:
                    self.last_seen = message[0]
                    yield (message[0], message[1]) if include_sequence_id else message[1]
            if caught_up is not None:
                caught_up.set()
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
    projection.reset_last_seen(0)

    yield message_bus._instance

    message_bus._instance = backup


@pytest.fixture
def fake_storage():
    backup = storage._instance
    storage._instance = AsyncMock()
    storage._instance.add = AsyncMock()
    storage._instance.update = AsyncMock()
    storage._instance.delete = AsyncMock()
    storage._instance.fetch = AsyncMock()
    storage._instance.ensure_schema = AsyncMock()

    yield storage._instance

    storage._instance = backup


def with_events(events):
    def with_events_wrapper(f):
        @wraps(f)
        async def call_with_events(*args, **kwargs):
            message_bus.message_bus().topic("users").messages = \
                    [(n+1, e) for n, e in enumerate(events)]
            return await f(*args, **kwargs)
        return call_with_events
    return with_events_wrapper


@pytest.mark.asyncio
@with_events([{"type": "created",
               "payload": {
                   "username": "alice",
                   "name": "Alice",
                   "summary": "Engineer",
                   "resume": {"experience": []}}}])
async def test_handle_user_events_created(fake_storage, fake_message_bus):
    await projection.handle_user_events()

    fake_storage.add.assert_awaited_once()
    fake_storage.update.assert_not_awaited()
    fake_storage.delete.assert_not_awaited()


@pytest.mark.asyncio
@with_events([{"type": "updated",
               "payload": {
                   "username": "alice",
                   "name": "Alice Updated",
                   "summary": "Architect",
                   "resume": {"experience": []}}}])
async def test_handle_user_events_updated(fake_storage, fake_message_bus):
    await projection.handle_user_events()

    fake_storage.update.assert_awaited_once()
    fake_storage.add.assert_not_awaited()
    fake_storage.delete.assert_not_awaited()


@pytest.mark.asyncio
@with_events([{"type": "deleted",
               "payload": {"username": "alice"}}])
async def test_handle_user_events_deleted(fake_storage, fake_message_bus):
    await projection.handle_user_events()

    fake_storage.delete.assert_awaited_once()
    fake_storage.add.assert_not_awaited()
    fake_storage.update.assert_not_awaited()


@pytest.mark.asyncio
@with_events([{"type": "unknown",
               "payload": {"username": "alice"}}])
async def test_handle_user_events_ignores_unknown_type(fake_storage, fake_message_bus):
    await projection.handle_user_events()

    fake_storage.add.assert_not_awaited()
    fake_storage.update.assert_not_awaited()
    fake_storage.delete.assert_not_awaited()


@pytest.mark.asyncio
@with_events([{"type": "created",
               "payload": {"username": "old"}},
              {"type": "unknown",
               "payload": {"username": "alice"}},
              {"type": "created",
               "payload": {"username": "new",
                           "name": "New User",
                           "resume": {"experience": []}}}])
async def test_handle_user_events_skips_messages_before_last_seen(fake_storage, fake_message_bus):
    projection.reset_last_seen(2)
    await projection.handle_user_events()

    fake_storage.add.assert_awaited_once()


@pytest.mark.asyncio
@with_events([{"type": "created"}])
async def test_handle_user_events_missing_payload(fake_storage, fake_message_bus):
    await projection.handle_user_events()

    fake_storage.add.assert_not_awaited()
    fake_storage.update.assert_not_awaited()
    fake_storage.delete.assert_not_awaited()



@pytest.mark.asyncio
@with_events([{"type": "created",
               "payload": {
                  # missing username
                  "name": "Alice"}}])
async def test_handle_user_events_malformed_payload_raises(fake_storage, fake_message_bus):
    await projection.handle_user_events()

    fake_storage.add.assert_not_awaited()
    fake_storage.update.assert_not_awaited()
    fake_storage.delete.assert_not_awaited()

