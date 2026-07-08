# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone
from functools import wraps
from unittest.mock import AsyncMock, MagicMock
from profed.core import message_bus
from profed.components.api.s2s.outbox import storage
from profed.components.api.s2s.outbox import projection


TS = datetime(2026, 1, 1, tzinfo=timezone.utc)
ALICE_URL = "https://example.com/actors/alice"
BOB_URL = "https://example.com/actors/bob"


def _activity(id_, type_, actor, object_):
    return {"id": id_, "type": type_, "actor": actor, "object": object_}


@pytest.fixture
def fake_storage():
    backup = storage._instance
    storage._instance = AsyncMock()
    storage._instance.add = AsyncMock()
    storage._instance.ensure_schema = AsyncMock()
    storage._instance.rebuild_finished = MagicMock()

    yield storage._instance

    storage._instance = backup


@pytest.fixture(autouse=True)
def reset_projection():
    projection.reset_last_seen(0)


def with_activities(activities):
    def wrapper(f):
        @wraps(f)
        async def call(*args, **kwargs):
            message_bus.message_bus().topic("activities").messages = [
                    (n+1, et, oid, TS, p)
                    for n, (et, oid, p) in enumerate(activities)]
            return await f(*args, **kwargs)
        return call
    return wrapper


def with_snapshots(snapshots):
    def wrapper(f):
        @wraps(f)
        async def call(*args, **kwargs):
            message_bus.message_bus().topic("activities").snapshots = snapshots
            return await f(*args, **kwargs)
        return call
    return wrapper


CREATE_ID = f"{ALICE_URL}#create/1"
CREATE = _activity(CREATE_ID, "Create", ALICE_URL, {"id": f"{ALICE_URL}/notes/1"})


@pytest.mark.asyncio
@with_snapshots([(42, [{"username": "alice", "activity": CREATE}])])
async def test_rebuild_success(fake_storage, fake_bus):
    await projection.rebuild()

    fake_storage.ensure_schema.assert_awaited_once()
    fake_storage.add.assert_awaited_once_with("alice", CREATE)


@pytest.mark.asyncio
@with_snapshots([])
async def test_rebuild_no_snapshot(fake_storage, fake_bus):
    await projection.rebuild()

    fake_storage.ensure_schema.assert_awaited_once()
    fake_storage.add.assert_not_awaited()


@pytest.mark.asyncio
@with_snapshots([(42, [{"username": "alice", "activity": CREATE}])])
async def test_rebuild_add_failure(fake_storage, fake_bus):
    fake_storage.add.side_effect = RuntimeError("DB error")

    with pytest.raises(RuntimeError, match="DB error"):
        await projection.rebuild()


@pytest.mark.asyncio
@with_snapshots([(10, [{"username": "alice", "activity": CREATE},
                       {"username": "alice",
                        "activity": _activity(f"{ALICE_URL}#update/1",
                                              "Update",
                                              ALICE_URL,
                                              {"id": f"{ALICE_URL}/notes/1"})}])])
async def test_rebuild_multiple_activities(fake_storage, fake_bus):
    await projection.rebuild()

    assert fake_storage.add.await_count == 2


@pytest.mark.asyncio
@with_snapshots([(5, [{"activity": CREATE}])])
async def test_rebuild_invalid_snapshot_item(fake_storage, fake_bus):
    await projection.rebuild()

    fake_storage.add.assert_not_awaited()


@pytest.mark.asyncio
@with_snapshots([(10,
                  [{"username": "alice", "activity": CREATE},
                   {"username": "", "activity": CREATE},
                   {"activity": CREATE},
                   {"username": "bob",
                    "activity": _activity(f"{BOB_URL}#create/1",
                                          "Create",
                                          BOB_URL,
                                          {"id": f"{BOB_URL}/notes/1"})}])])
async def test_rebuild_multiple_items_some_malformed(fake_storage, fake_bus):
    await projection.rebuild()

    assert fake_storage.add.await_count == 2


CREATE_PAYLOAD = {"username": "alice",
                  "activity": {"actor":  ALICE_URL,
                               "object": {"id": f"{ALICE_URL}/notes/1"}}}


@pytest.mark.asyncio
@with_activities([("Create", CREATE_ID, CREATE_PAYLOAD)])
async def test_handle_user_events_create(fake_storage, fake_bus):
    await projection.handle_user_events()

    fake_storage.add.assert_awaited_once_with("alice",
                                              {"id": CREATE_ID,
                                               "type": "Create",
                                               "actor": ALICE_URL,
                                               "object": {"id": f"{ALICE_URL}/notes/1"}})


@pytest.mark.asyncio
@with_activities([("renamed", CREATE_ID, CREATE_PAYLOAD)])
async def test_handle_user_events_ignores_unknown_verb(fake_storage, fake_bus):
    await projection.handle_user_events()

    fake_storage.add.assert_not_awaited()


@pytest.mark.asyncio
@with_activities([("Create",
                   CREATE_ID,
                   {"activity": {"actor": ALICE_URL}})])
async def test_handle_user_events_ignores_malformed_event(fake_storage, fake_bus):
    await projection.handle_user_events()

    fake_storage.add.assert_not_awaited()


@pytest.mark.asyncio
@with_activities([("Create", CREATE_ID, {"activity": {"actor": ALICE_URL}}),
                  ("Create", CREATE_ID, CREATE_PAYLOAD)])
async def test_handle_user_events_continues_after_malformed_event(fake_storage, fake_bus):
    await projection.handle_user_events()

    fake_storage.add.assert_awaited_once_with("alice",
                                              {"id": CREATE_ID,
                                               "type": "Create",
                                               "actor": ALICE_URL,
                                               "object": {"id": f"{ALICE_URL}/notes/1"}})

