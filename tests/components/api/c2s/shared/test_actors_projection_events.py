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
ACCOUNT = {"id": "1",
           "username": "alice",
           "acct": "alice@example.com",
           "display_name": "Alice",
           "followers_count": 2,
           "following_count": 3,
           "statuses_count":  5}


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
            message_bus.message_bus().topic("accounts").messages = [
                    (n+1, et, oid, TS, p)
                    for n, (et, oid, p) in enumerate(events)]
            return await f(*args, **kwargs)
        return call_with_events
    return with_events_wrapper


@with_events([("created", "alice", ACCOUNT)])
async def test_created_stores_account(fake_storage, fake_bus):
    await projection.handle_account_events()

    assert fake_storage.rows["alice"] == ACCOUNT


@pytest.mark.asyncio
@with_events([("created", "alice", ACCOUNT),
              ("updated", "alice", {**ACCOUNT, "display_name": "Alice Updated"})])
async def test_updated_replaces_account(fake_storage, fake_bus):
    await projection.handle_account_events()

    assert fake_storage.rows["alice"]["display_name"] == "Alice Updated"


@with_events([("created", "alice", ACCOUNT),
              ("followers_changed", "alice", {"count": 9})])
async def test_followers_changed_updates_only_followers(fake_storage, fake_bus):
    await projection.handle_account_events()

    assert fake_storage.rows["alice"]["followers_count"] == 9
    assert fake_storage.rows["alice"]["following_count"] == 3


@with_events([("created", "alice", ACCOUNT),
              ("statuses_changed", "alice", {"count": 7})])
async def test_statuses_changed_updates_count(fake_storage, fake_bus):
    await projection.handle_account_events()

    assert fake_storage.rows["alice"]["statuses_count"] == 7


@pytest.mark.asyncio
@with_events([("created", "alice", ACCOUNT),
              ("deleted", "alice", {})])
async def test_deleted_removes_account(fake_storage, fake_bus):
    await projection.handle_account_events()

    assert "alice" not in fake_storage.rows

