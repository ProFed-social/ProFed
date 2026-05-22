# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from functools import wraps
from unittest.mock import AsyncMock, Mock
from profed.components.api.s2s.webfinger import storage
from profed.components.api.s2s.webfinger import projection
from profed.core import message_bus

from _fakes import FakeMessageBus


@pytest.fixture
def fake_message_bus():
    backup = message_bus._instance
    message_bus._instance = FakeMessageBus()
    projection.reset_last_seen(0)

    yield message_bus._instance

    message_bus._instance = backup


@pytest.fixture
def fake_storage():
    instance = Mock()
    instance.add = AsyncMock()
    instance.delete = AsyncMock()
    instance.exists = AsyncMock()
    instance.ensure_schema = AsyncMock()

    storage.overwrite(instance)

    return instance


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
    await projection.handle_user_events()

    fake_storage.add.assert_awaited_with("bob")


@pytest.mark.asyncio
@with_events([{"type": "deleted",
               "payload": {"username": "bob"}}])
async def test_user_event_processing_delete_event(fake_storage, fake_message_bus):
    await projection.handle_user_events()

    fake_storage.delete.assert_awaited_once_with("bob")

@pytest.mark.asyncio
@with_events([{"type": "unknown_event", "payload": {"username": "alice"}}])
async def test_user_event_processing_unknown_event(fake_storage, fake_message_bus):
    await projection.handle_user_events()

    fake_storage.add.assert_not_awaited()
    fake_storage.delete.assert_not_awaited()


@pytest.mark.asyncio
@with_events([{"type": "created", "payload": {"username": "bob"}},
              {"type": "updated", "payload": {"username": "bob"}},
              {"type": "deleted", "payload": {"username": "bob"}}])
async def test_event_processing_multiple_messages(fake_storage, fake_message_bus):
    await projection.handle_user_events()

    assert fake_storage.add.await_count == 1
    assert fake_storage.delete.await_count == 1


@pytest.mark.asyncio
@with_events([{"type": "created"}])
async def test_event_processing_invalid_message(fake_storage, fake_message_bus):
    await projection.handle_user_events()

    fake_storage.add.assert_not_awaited()
    fake_storage.delete.assert_not_awaited()


@pytest.mark.asyncio
@with_events([{"type": "created", "payload": {}}])
async def test_event_processing_malformed_payload_raises(fake_storage, fake_message_bus):
    await projection.handle_user_events()

    fake_storage.add.assert_not_awaited()
    fake_storage.delete.assert_not_awaited()

