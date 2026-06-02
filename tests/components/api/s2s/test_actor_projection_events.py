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

    assert fake_storage.rows["alice"] == {"name": "Alice",
                                          "summary": "Engineer",
                                          "username": "alice"}


@pytest.mark.asyncio
@with_events([("created", "alice", {"name": "Alice", "summary": "Engineer"}),
              ("profile_edited", "alice", {"name": "Alice Updated"})])
async def test_profile_edited_merges_keeps_other_fields(fake_storage, fake_bus):
    await projection.handle_user_events()

    assert fake_storage.rows["alice"] == {"name": "Alice Updated",
                                          "summary": "Engineer",
                                          "username": "alice"}


@pytest.mark.asyncio
@with_events([("created", "alice", {"name": "Alice",
                                    "avatar": {"media_id": "m-old", "variants": ["large", "small"]}}),
              ("avatar_changed", "alice", {"media_id": "m-new", "variants": ["large", "small"]})])
async def test_avatar_changed_sets_reference_keeps_name(fake_storage, fake_bus):
    await projection.handle_user_events()

    assert fake_storage.rows["alice"]["avatar"] == {"media_id": "m-new",
                                                    "variants": {"large", "small"}}
    assert fake_storage.rows["alice"]["name"] == "Alice"


@pytest.mark.asyncio
@with_events([("created", "alice", {"name": "Alice",
                                    "avatar": {"media_id": "m1", "variants": ["large"]}}),
              ("avatar_changed", "alice", {})])
async def test_avatar_changed_empty_clears_only_avatar(fake_storage, fake_bus):
    await projection.handle_user_events()

    assert fake_storage.rows["alice"]["avatar"] is None
    assert fake_storage.rows["alice"]["name"] == "Alice"


@pytest.mark.asyncio
@with_events([("created", "alice", {"name": "Alice"}),
              ("header_changed", "alice", {"media_id": "h1", "variants": ["wide"]})])
async def test_header_changed_sets_reference(fake_storage, fake_bus):
    await projection.handle_user_events()

    assert fake_storage.rows["alice"]["header"] == {"media_id": "h1", "variants": {"wide"}}


@pytest.mark.asyncio
@with_events([("created", "alice", {"name": "Alice"}),
              ("cv_changed", "alice", {"resume": {"experience": []}})])
async def test_cv_changed_sets_resume_keeps_name(fake_storage, fake_bus):
    await projection.handle_user_events()

    assert fake_storage.rows["alice"]["resume"]["experience"] == []
    assert fake_storage.rows["alice"]["name"] == "Alice"


@pytest.mark.asyncio
@with_events([("created", "alice", {"name": "Alice", "public_key_pem": "OLD"}),
              ("keys_generated", "alice", {"public_key_pem": "PUB",
                                           "private_key_pem": "PRIV"})])
async def test_keys_generated_merges_keys(fake_storage, fake_bus):
    await projection.handle_user_events()

    assert fake_storage.rows["alice"]["public_key_pem"] == "PUB"
    assert fake_storage.rows["alice"]["private_key_pem"] == "PRIV"
    assert fake_storage.rows["alice"]["name"] == "Alice"


@pytest.mark.asyncio
@with_events([("created", "alice", {"name": "Alice"}),
              ("deleted", "alice", {})])
async def test_deleted_removes_user(fake_storage, fake_bus):
    await projection.handle_user_events()

    assert "alice" not in fake_storage.rows


@pytest.mark.asyncio
@with_events([("unknown", "alice", {})])
async def test_unknown_type_is_ignored(fake_storage, fake_bus):
    await projection.handle_user_events()

    assert fake_storage.rows == {}


@pytest.mark.asyncio
@with_events([("created", "alice", {"name": "Alice"}),
              ("deleted", "alice", {"name": "Alice"})])
async def test_deleted_with_non_empty_payload_is_ignored(fake_storage, fake_bus):
    await projection.handle_user_events()

    assert "alice" in fake_storage.rows


@pytest.mark.asyncio
@with_events([("created", "alice", {"foo": "bar"})])
async def test_malformed_payload_is_ignored(fake_storage, fake_bus):
    await projection.handle_user_events()

    assert fake_storage.rows == {}


@pytest.mark.asyncio
@with_events([("created", "old", {"name": "Old"}),
              ("unknown", "x", {}),
              ("created", "new", {"name": "New User"})])
async def test_skips_messages_before_last_seen(fake_storage, fake_bus):
    projection.reset_last_seen(2)

    await projection.handle_user_events()
    assert "new" in fake_storage.rows
    assert "old" not in fake_storage.rows

