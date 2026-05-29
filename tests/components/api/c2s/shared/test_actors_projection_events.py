# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone
from functools import wraps
from _fakes import FakeKeyValueStorage
from profed.core import message_bus
from profed.components.api.c2s.shared.actors import storage
from profed.components.api.c2s.shared.actors import projection


TS = datetime(2026, 1, 1, tzinfo=timezone.utc)


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
            message_bus.message_bus().topic("users").messages = [
                    (n+1, et, oid, TS, p)
                    for n, (et, oid, p) in enumerate(events)]
            return await f(*args, **kwargs)
        return call_with_events
    return with_events_wrapper


@pytest.mark.asyncio
@with_events([("created", "alice", {"name": "Alice", "summary": "Engineer"})])
async def test_created_adds_full_payload(fake_storage, fake_bus):
    await projection.handle_user_events()

    assert fake_storage.rows["alice"] == {"name":     "Alice",
                                          "summary":  "Engineer",
                                          "username": "alice"}


@pytest.mark.asyncio
@with_events([("created",        "alice", {"name": "Alice", "summary": "Engineer"}),
              ("profile_edited", "alice", {"name": "Alice Updated"})])
async def test_profile_edited_merges_keeps_other_fields(fake_storage, fake_bus):
    await projection.handle_user_events()

    assert fake_storage.rows["alice"] == {"name":     "Alice Updated",
                                          "summary":  "Engineer",
                                          "username": "alice"}


@pytest.mark.asyncio
@with_events([("created",        "alice", {"name": "Alice", "avatar_url": "https://x/a.png"}),
              ("avatar_changed", "alice", {})])
async def test_avatar_changed_empty_clears_only_avatar(fake_storage, fake_bus):
    await projection.handle_user_events()

    assert fake_storage.rows["alice"]["avatar_url"] is None
    assert fake_storage.rows["alice"]["name"]       == "Alice"


@pytest.mark.asyncio
@with_events([("created", "alice", {"name": "Alice"}),
              ("deleted", "alice", {})])
async def test_deleted_removes_user(fake_storage, fake_bus):
    await projection.handle_user_events()

    assert "alice" not in fake_storage.rows

