# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone
from functools import wraps
from unittest.mock import AsyncMock
from profed.core import message_bus
from profed.components.api.s2s.actor import storage
from profed.components.api.s2s.actor import projection


TS = datetime(2026, 1, 1, tzinfo=timezone.utc)


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
    """events: list of (event_type, object_id, payload) tuples"""
    def with_events_wrapper(f):
        @wraps(f)
        async def call_with_events(*args, **kwargs):
            message_bus.message_bus().topic("users").messages = [
                    (n+1, et, oid, TS, p)
                    for n, (et, oid, p) in enumerate(events)]
            return await f(*args, **kwargs)
        return call_with_events
    return with_events_wrapper


@pytest.mark.asyncio
@with_events([("created", "alice",
               {"name": "Alice",
                "summary": "Engineer",
                "resume": {"experience": []}})])
async def test_handle_user_events_created(fake_storage, fake_bus):

    await projection.handle_user_events()
    fake_storage.add.assert_awaited_once()
    fake_storage.update.assert_not_awaited()
    fake_storage.delete.assert_not_awaited()


@pytest.mark.asyncio
@with_events([("created", "alice", {"name": "Alice"}),
              ("profile_edited", "alice", {"name": "Alice Updated"})])
async def test_profile_edited_updates(fake_storage, fake_bus):
    await projection.handle_user_events()
    fake_storage.update.assert_awaited_once_with("alice", {"name": "Alice Updated"})


@pytest.mark.asyncio
@with_events([("created", "alice", {"name": "Alice"}),
              ("avatar_changed", "alice", {"url": "https://x/a.png"})])
async def test_avatar_changed_updates_avatar_url(fake_storage, fake_bus):
    await projection.handle_user_events()
    fake_storage.update.assert_awaited_once_with("alice", {"avatar_url": "https://x/a.png"})


@pytest.mark.asyncio
@with_events([("created", "alice", {"name": "Alice"}),
              ("avatar_changed", "alice", {})])
async def test_avatar_changed_empty_clears_avatar_url(fake_storage, fake_bus):
    await projection.handle_user_events()
    fake_storage.update.assert_awaited_once_with("alice", {"avatar_url": None})


@pytest.mark.asyncio
@with_events([("created", "alice", {"name": "Alice"}),
              ("header_changed", "alice", {"url": "https://x/h.jpg"})])
async def test_header_changed_updates_header_url(fake_storage, fake_bus):
    await projection.handle_user_events()
    fake_storage.update.assert_awaited_once_with("alice", {"header_url": "https://x/h.jpg"})


@pytest.mark.asyncio
@with_events([("created", "alice", {"name": "Alice"}),
              ("cv_changed", "alice", {"resume": {"experience": []}})])
async def test_cv_changed_updates_resume(fake_storage, fake_bus):
    await projection.handle_user_events()
    fake_storage.update.assert_awaited_once_with("alice", {"resume": {"experience": []}})


@pytest.mark.asyncio
@with_events([("created", "alice", {"name": "Alice"}),
              ("keys_generated", "alice",
               {"public_key_pem": "PUB", "private_key_pem": "PRIV"})])
async def test_keys_generated_updates_keys(fake_storage, fake_bus):
    await projection.handle_user_events()
    fake_storage.update.assert_awaited_once_with("alice",
                                                 {"public_key_pem": "PUB",
                                                  "private_key_pem": "PRIV"})


@pytest.mark.asyncio
@with_events([("deleted", "alice", {})])
async def test_handle_user_events_deleted(fake_storage, fake_bus):
    await projection.handle_user_events()

    fake_storage.delete.assert_awaited_once_with("alice")
    fake_storage.add.assert_not_awaited()
    fake_storage.update.assert_not_awaited()


@pytest.mark.asyncio
@with_events([("unknown", "alice", {})])
async def test_handle_user_events_ignores_unknown_type(fake_storage, fake_bus):
    await projection.handle_user_events()

    fake_storage.add.assert_not_awaited()
    fake_storage.update.assert_not_awaited()
    fake_storage.delete.assert_not_awaited()


@pytest.mark.asyncio
@with_events([("created", "old", {}),
              ("unknown", "alice", {}),
              ("created", "new", {"name":   "New User",
                                  "resume": {"experience": []}})])
async def test_handle_user_events_skips_messages_before_last_seen(fake_storage, fake_bus):
    projection.reset_last_seen(2)

    await projection.handle_user_events()

    fake_storage.add.assert_awaited_once()


@pytest.mark.asyncio
@with_events([("deleted", "alice", {"name": "Alice"})])
async def test_handle_user_events_deleted_with_non_empty_payload_is_ignored(fake_storage, fake_bus):
    await projection.handle_user_events()

    fake_storage.delete.assert_not_awaited()


@pytest.mark.asyncio
@with_events([("created", "alice", {"name": 42})])
async def test_handle_user_events_malformed_payload_is_ignored(fake_storage, fake_bus):
    await projection.handle_user_events()

    fake_storage.add.assert_not_awaited()

