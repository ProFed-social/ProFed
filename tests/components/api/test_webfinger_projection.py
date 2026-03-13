# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from functools import wraps
from unittest.mock import AsyncMock, Mock
from profed.components.api.projections import rebuild_webfinger_projection


@pytest.fixture
def fake_storage():
    store = Mock()
    store.add = AsyncMock()
    store.update = AsyncMock()
    store.delete = AsyncMock()
    store.fetch_actor_url = AsyncMock()
    return store


def with_snapshot(last_seen, snapshot):
    def with_snapshot_wrapper(f):
        @wraps(f)
        async def call_with_snapshot(*args, **kwargs):
            fake_bus = Mock()

            async def fake_last_snapshot():
                return (last_seen, snapshot)

            fake_bus.topic.return_value.last_snapshot = fake_last_snapshot

            return f(*args, **kwargs)
        return call_with_snapshot
    return with_snapshot_wrapper


@pytest.mark.asyncio
@with_snapshot(42,
               [{"acct": "alice@example.com",
                 "actor_url": "https://example.com/alice"}])
async def test_rebuild_webfinger_projection_success(fake_storage):
    await rebuild_webfinger_projection()
    fake_storage.add.assert_awaited_once_with("alice@example.com", "https://example.com/alice")


@pytest.mark.asyncio
@with_snapshot(None, [])
async def test_rebuild_webfinger_projection_no_snapshot(fake_storage):
    await rebuild_webfinger_projection()
    fake_storage.add.assert_not_awaited()


@pytest.mark.asyncio
@with_snapshot(42,
               [{"acct": "alice@example.com",
                 "actor_url": "https://example.com/alice"}])
async def test_rebuild_webfinger_projection_add_failure(fake_storage):
    fake_storage.add.side_effect = RuntimeError("DB error")

    with pytest.raises(RuntimeError, match="DB error"):
        await rebuild_webfinger_projection()


@pytest.mark.asyncio
@with_snapshot(10,
               [{"acct": "alice@example.com",
                 "actor_url": "https://example.com/alice"},
                {"acct": "bob@example.com",
                 "actor_url": "https://example.com/bob"}])
async def test_projection_multiple_users(fake_storage):
    await rebuild_webfinger_projection()
    assert fake_storage.add.await_count == 2


@pytest.mark.asyncio
@with_snapshot(5, [{"acct": "alice@example.com"}])
async def test_projection_invalid_payload(fake_storage):
    await rebuild_webfinger_projection()
    assert fake_storage.add.await_count == 0


@pytest.mark.asyncio
@with_snapshot(10,
               [{"acct": "alice@example.com",
                 "actor_url": "https://example.com/alice"},
                {"acct": "bob@example.com",
                 "actor_url": "https://example.com/bob"},
                {"acct": "alice@example.com"}])
async def test_projection_multiple_users_one_malformed(fake_storage):
    await rebuild_webfinger_projection()
    assert fake_storage.add.await_count == 2

