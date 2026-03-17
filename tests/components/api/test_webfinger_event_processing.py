# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from functools import wraps
from unittest.mock import AsyncMock, Mock
from profed.components.api.storage import webfinger as storage
from profed.components.api.projections import webfinger as projections
from profed.core import message_bus


class FakeTopic:
    def __init__(self):
        self.last_seen = 0
        self.snapshots = []
        self.messages = []

    async def last_snapshot(self):
        return self.snapshots[-1] if len(self.snapshots) > 0 else (0, [])

    def subscribe(self, last_seen: int = 0):
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
    projections.reset_last_seen(0)

    yield message_bus._instance

    message_bus._instance = backup


@pytest.fixture
def fake_storage():
    backup = storage._instance
    storage._instance = Mock()
    storage._instance.add = AsyncMock()
    storage._instance.delete = AsyncMock()
    storage._instance.user_exists = AsyncMock()
    storage._instance.ensure_table = AsyncMock()

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
               "payload": {"username": "bob"}}])
async def test_user_added_event(fake_storage, fake_message_bus):
    await projections.handle_user_events()

    fake_storage.add.assert_awaited_with("bob")


@pytest.mark.asyncio
@with_events([{"type": "deleted",
               "payload": {"username": "bob"}}])
async def test_user_event_processing_delete_event(fake_storage, fake_message_bus):
    await projections.handle_user_events()

    fake_storage.delete.assert_awaited_once_with("bob")

@pytest.mark.asyncio
@with_events([{"type": "unknown_event", "payload": {"username": "alice"}}])
async def test_user_event_processing_unknown_event(fake_storage, fake_message_bus):
    await projections.handle_user_events()

    fake_storage.add.assert_not_awaited()
    fake_storage.delete.assert_not_awaited()


@pytest.mark.asyncio
@with_events([{"type": "created", "payload": {"username": "bob"}},
              {"type": "updated", "payload": {"username": "bob"}},
              {"type": "deleted", "payload": {"username": "bob"}}])
async def test_event_processing_multiple_messages(fake_storage, fake_message_bus):
    await projections.handle_user_events()

    assert fake_storage.add.await_count == 1
    assert fake_storage.delete.await_count == 1


@pytest.mark.asyncio
@with_events([{"type": "created"}])
async def test_event_processing_invalid_message(fake_storage, fake_message_bus):
    await projections.handle_user_events()

    fake_storage.add.assert_not_awaited()
    fake_storage.delete.assert_not_awaited()


@pytest.mark.asyncio
@with_events([{"type": "created", "payload": {}}])
async def test_event_processing_malformed_payload_raises(fake_storage, fake_message_bus):
    await projections.handle_user_events()

    fake_storage.add.assert_not_awaited()
    fake_storage.delete.assert_not_awaited()

