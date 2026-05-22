# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from functools import wraps
from unittest.mock import AsyncMock, Mock
from profed.core import message_bus
from profed.components.api.s2s.actor import storage
from profed.components.api.s2s.actor import projection


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
async def test_handle_user_events_created(fake_storage, fake_bus):
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
async def test_handle_user_events_updated(fake_storage, fake_bus):
    await projection.handle_user_events()

    fake_storage.update.assert_awaited_once()
    fake_storage.add.assert_not_awaited()
    fake_storage.delete.assert_not_awaited()


@pytest.mark.asyncio
@with_events([{"type": "deleted",
               "payload": {"username": "alice"}}])
async def test_handle_user_events_deleted(fake_storage, fake_bus):
    await projection.handle_user_events()

    fake_storage.delete.assert_awaited_once()
    fake_storage.add.assert_not_awaited()
    fake_storage.update.assert_not_awaited()


@pytest.mark.asyncio
@with_events([{"type": "unknown",
               "payload": {"username": "alice"}}])
async def test_handle_user_events_ignores_unknown_type(fake_storage, fake_bus):
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
async def test_handle_user_events_skips_messages_before_last_seen(fake_storage, fake_bus):
    projection.reset_last_seen(2)
    await projection.handle_user_events()

    fake_storage.add.assert_awaited_once()


@pytest.mark.asyncio
@with_events([{"type": "created"}])
async def test_handle_user_events_missing_payload(fake_storage, fake_bus):
    await projection.handle_user_events()

    fake_storage.add.assert_not_awaited()
    fake_storage.update.assert_not_awaited()
    fake_storage.delete.assert_not_awaited()



@pytest.mark.asyncio
@with_events([{"type": "created",
               "payload": {
                  # missing username
                  "name": "Alice"}}])
async def test_handle_user_events_malformed_payload_raises(fake_storage, fake_bus):
    await projection.handle_user_events()

    fake_storage.add.assert_not_awaited()
    fake_storage.update.assert_not_awaited()
    fake_storage.delete.assert_not_awaited()

