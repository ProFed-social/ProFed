# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from functools import wraps
from unittest.mock import AsyncMock
from profed.core import message_bus
from profed.components.api.storage import outbox as storage
from profed.components.api.projections import outbox as projections


class FakeTopic:
    def __init__(self):
        self.last_seen = 0
        self.snapshots = []
        self.messages = []

    async def last_snapshot(self):
        return self.snapshots[-1] if len(self.snapshots) > 0 else (0, [])

    def subscribe(self, subscriber: str, last_seen: int = 0):
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
    storage._instance = AsyncMock()
    storage._instance.add = AsyncMock()
    storage._instance.ensure_table = AsyncMock()

    yield storage._instance

    storage._instance = backup


def with_activities(activities):
    def with_events_wrapper(f):
        @wraps(f)
        async def call_with_events(*args, **kwargs):
            message_bus.message_bus().topic("activities").messages = \
                    [(n+1, e) for n, e in enumerate(activities)]
            return await f(*args, **kwargs)
        return call_with_events
    return with_events_wrapper


def with_snapshots(snapshots):
    def with_events_wrapper(f):
        @wraps(f)
        async def call_with_events(*args, **kwargs):
            message_bus.message_bus().topic("activities").snapshots = snapshots
            return await f(*args, **kwargs)
        return call_with_events
    return with_events_wrapper


@pytest.mark.asyncio
@with_snapshots([(42,
                  [{"username": "alice",
                    "type": "created",
                    "actor": "https://example.com/actors/alice",
                    "object": {"id": "https://example.com/actors/alice"}}])])
async def test_rebuild_success(fake_storage, fake_message_bus):
    await projections.rebuild()

    fake_storage.ensure_table.assert_awaited_once()
    fake_storage.add.assert_awaited_once_with("alice",
                                              {"username": "alice",
                                               "type": "created",
                                               "actor": "https://example.com/actors/alice",
                                               "object": {"id": "https://example.com/actors/alice"}})


@pytest.mark.asyncio
@with_snapshots([(0, [])])
async def test_rebuild_no_snapshot(fake_storage, fake_message_bus):
    await projections.rebuild()

    fake_storage.ensure_table.assert_awaited_once()
    fake_storage.add.assert_not_awaited()


@pytest.mark.asyncio
@with_snapshots([(42,
                  [{"username": "alice",
                    "type": "created",
                    "actor": "https://example.com/actors/alice",
                    "object": {"id": "https://example.com/actors/alice"}}])])
async def test_rebuild_add_failure(fake_storage, fake_message_bus):
    fake_storage.add.side_effect = RuntimeError("DB error")

    with pytest.raises(RuntimeError, match="DB error"):
        await projections.rebuild()


@pytest.mark.asyncio
@with_snapshots([(10,
                  [{"username": "alice",
                    "type": "created",
                    "actor": "https://example.com/actors/alice",
                    "object": {"id": "https://example.com/actors/alice"}},
                   {"username": "alice",
                    "type": "Update",
                    "actor": "https://example.com/actors/alice",
                    "object": {"id": "https://example.com/actors/alice"}}])])
async def test_rebuild_multiple_activities(fake_storage, fake_message_bus):
    await projections.rebuild()

    assert fake_storage.add.await_count == 2


@pytest.mark.asyncio
@with_snapshots([(5,
                  [{"type": "created",
                    "actor": "https://example.com/actors/alice",
                    "object": {"id": "https://example.com/actors/alice"}}])])
async def test_rebuild_invalid_snapshot_item(fake_storage, fake_message_bus):
    await projections.rebuild()

    fake_storage.add.assert_not_awaited()


@pytest.mark.asyncio
@with_snapshots([(10,
                  [{"username": "alice",
                    "type": "created",
                    "actor": "https://example.com/actors/alice",
                    "object": {"id": "https://example.com/actors/alice"}},
                   {"username": "",
                    "type": "created",
                    "actor": "https://example.com/actors/alice",
                    "object": {"id": "https://example.com/actors/alice"}},
                   {"type": "created",
                    "actor": "https://example.com/actors/alice",
                    "object": {"id": "https://example.com/actors/alice"}},
                   {"username": "bob",
                    "type": "created",
                    "actor": "https://example.com/actors/bob",
                    "object": {"id": "https://example.com/actors/bob"}}])])
async def test_rebuild_multiple_items_some_malformed(fake_storage, fake_message_bus):
    await projections.rebuild()

    assert fake_storage.add.await_count == 2


@pytest.mark.asyncio
@with_activities([{"type": "created",
                   "payload": {"username": "alice",
                               "type": "created",
                               "actor": "https://example.com/actors/alice",
                               "object": {"id": "https://example.com/actors/alice"}}}])
async def test_handle_user_events_created(fake_storage, fake_message_bus):
    await projections.handle_user_events()

    fake_storage.add.assert_awaited_once_with("alice",
                                              {"username": "alice",
                                               "type": "created",
                                               "actor": "https://example.com/actors/alice",
                                               "object": {"id": "https://example.com/actors/alice"}})


@pytest.mark.asyncio
@with_activities([{"type": "updated",
                   "payload": {"username": "alice",
                               "type": "Update",
                               "actor": "https://example.com/actors/alice",
                               "object": {"id": "https://example.com/actors/alice"}}}])
async def test_handle_user_events_ignores_unknown_event_type(fake_storage, fake_message_bus):
    await projections.handle_user_events()

    fake_storage.add.assert_not_awaited()


@pytest.mark.asyncio
@with_activities([{"type": "created",
                   "payload": {"type": "created",
                               "actor": "https://example.com/actors/alice",
                               "object": {"id": "https://example.com/actors/alice"}}}])
async def test_handle_user_events_ignores_malformed_event(fake_storage, fake_message_bus):
    await projections.handle_user_events()

    fake_storage.add.assert_not_awaited()


@pytest.mark.asyncio
@with_activities([{"type": "created",
                   "payload": {"type": "created",
                               "actor": "https://example.com/actors/alice",
                               "object": {"id": "https://example.com/actors/alice"}}},
                  {"type": "created",
                   "payload": {"username": "alice",
                               "type": "created",
                               "actor": "https://example.com/actors/alice",
                               "object": {"id": "https://example.com/actors/alice"}}}])
async def test_handle_user_events_continues_after_malformed_event(fake_storage, fake_message_bus):
    await projections.handle_user_events()

    fake_storage.add.assert_awaited_once_with("alice",
                                              {"username": "alice",
                                               "type": "created",
                                               "actor": "https://example.com/actors/alice",
                                               "object": {"id": "https://example.com/actors/alice"}})

