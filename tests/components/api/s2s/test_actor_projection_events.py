# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone
from functools import wraps
from _fakes import FakeKeyValueStorage
from profed.core import message_bus
from profed.components.api.s2s.actor import storage
from profed.components.api.s2s.actor import projection


TS = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _actor(username="alice", **extra):
    base = f"https://example.com/actors/{username}"
    return {"@context": "https://www.w3.org/ns/activitystreams",
            "id": base,
            "type": "Person",
            "preferredUsername": username,
            "inbox": f"{base}/inbox",
            "outbox": f"{base}/outbox",
            **extra}


@pytest.fixture
def fake_storage():
    backup = storage._instance
    storage._instance = FakeKeyValueStorage()
    yield storage._instance
    storage._instance = backup


def with_events(events):
    def with_events_wrapper(f):
        @wraps(f)
        async def call_with_events(*args, **kwargs):
            message_bus.message_bus().topic("person").messages = [(n + 1, et, oid, TS, p)
                                                                  for n, (et, oid, p) in enumerate(events)]
            return await f(*args, **kwargs)
        return call_with_events
    return with_events_wrapper


@pytest.mark.asyncio
@with_events([("created", "alice", _actor(name="Alice", summary="Engineer"))])
async def test_created_stores_full_actor(fake_storage, fake_bus):
    await projection.handle_user_events()

    assert fake_storage.rows["alice"] == _actor(name="Alice", summary="Engineer")


@pytest.mark.asyncio
@with_events([("created", "alice", _actor(name="Alice", summary="Engineer")),
              ("updated", "alice", _actor(name="Alice Updated"))])
async def test_updated_replaces_full_actor(fake_storage, fake_bus):
    await projection.handle_user_events()

    assert fake_storage.rows["alice"] == _actor(name="Alice Updated")
    assert "summary" not in fake_storage.rows["alice"]


@pytest.mark.asyncio
@with_events([("created", "alice", _actor(name="Alice")),
              ("deleted", "alice", {})])
async def test_deleted_removes_actor(fake_storage, fake_bus):
    await projection.handle_user_events()

    assert "alice" not in fake_storage.rows


@pytest.mark.asyncio
@with_events([("created", "alice", _actor(name="Alice")),
              ("deleted", "alice", {"name": "Alice"})])
async def test_deleted_with_non_empty_payload_is_ignored(fake_storage, fake_bus):
    await projection.handle_user_events()

    assert "alice" in fake_storage.rows


@pytest.mark.asyncio
@with_events([("created", "alice", {"id": "x", "type": "Person"})])
async def test_created_without_preferred_username_is_ignored(fake_storage, fake_bus):
    await projection.handle_user_events()

    assert fake_storage.rows == {}


@pytest.mark.asyncio
@with_events([("created", "old", _actor("old")),
              ("unknown", "x", {}),
              ("created", "new", _actor("new"))])
async def test_skips_messages_before_last_seen(fake_storage, fake_bus):
    projection.reset_last_seen(2)

    await projection.handle_user_events()
    assert "new" in fake_storage.rows
    assert "old" not in fake_storage.rows

