# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone
from functools import wraps
from unittest.mock import AsyncMock, Mock
from profed.components.api.s2s.webfinger import storage
from profed.components.api.s2s.webfinger import projection
from profed.core import message_bus


TS = datetime(2026, 1, 1, tzinfo=timezone.utc)


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
    """events: list of (event_type, object_id, payload) tuples"""
    def wrapper(f):
        @wraps(f)
        async def call(*args, **kwargs):
            message_bus.message_bus().topic("person").messages = [
                    (n+1, et, oid, TS, p)
                    for n, (et, oid, p) in enumerate(events)]
            return await f(*args, **kwargs)
        return call
    return wrapper


@pytest.mark.asyncio
@with_events([("created", "bob", {"preferredUsername":"bob"})])
async def test_user_added_event(fake_storage, fake_bus):
    await projection.handle_user_events()

    fake_storage.add.assert_awaited_with("bob")


@pytest.mark.asyncio
@with_events([("deleted", "bob", {})])
async def test_user_event_processing_delete_event(fake_storage, fake_bus):
    await projection.handle_user_events()

    fake_storage.delete.assert_awaited_once_with("bob")


@pytest.mark.asyncio
@with_events([("unknown_event", "alice", {})])
async def test_user_event_processing_unknown_event(fake_storage, fake_bus):
    await projection.handle_user_events()

    fake_storage.add.assert_not_awaited()
    fake_storage.delete.assert_not_awaited()


@pytest.mark.asyncio
@with_events([("created", "bob", {"preferredUsername":"bob"}),
              ("updated", "bob", {}),
              ("deleted", "bob", {})])
async def test_event_processing_multiple_messages(fake_storage, fake_bus):
    await projection.handle_user_events()

    assert fake_storage.add.await_count    == 1
    assert fake_storage.delete.await_count == 1


@pytest.mark.asyncio
@with_events([("deleted", "alice", {"name": "Alice"})])
async def test_event_processing_deleted_with_non_empty_payload_is_ignored(fake_storage, fake_bus):
    await projection.handle_user_events()

    fake_storage.add.assert_not_awaited()
    fake_storage.delete.assert_not_awaited()

