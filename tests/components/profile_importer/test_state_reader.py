# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone
from profed.components.profile_importer import state_reader


TS = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _users(fake_bus):
    return fake_bus.topic("users")


def _msg(seq: int, event_type: str, object_id: str, payload: dict):
    return (seq, event_type, object_id, TS, payload)


@pytest.mark.asyncio
async def test_no_state_returns_none(fake_bus):
    async with state_reader.reading_state("alice") as (get_state, caught_up):
        await caught_up.wait()

        assert get_state() is None


@pytest.mark.asyncio
async def test_created_event_sets_state(fake_bus):
    _users(fake_bus).messages = [_msg(1, "created", "alice", {"name": "Alice"})]

    async with state_reader.reading_state("alice") as (get_state, caught_up):
        await caught_up.wait()

        profile = get_state()
    assert profile is not None
    assert profile.username == "alice"
    assert profile.name     == "Alice"


@pytest.mark.asyncio
async def test_updated_event_replaces_state(fake_bus):
    _users(fake_bus).messages = [_msg(1, "created", "alice", {"name": "Alice"}),
                                 _msg(2, "updated", "alice", {"name": "Alice Updated"})]

    async with state_reader.reading_state("alice") as (get_state, caught_up):
        await caught_up.wait()

        profile = get_state()
    assert profile.name == "Alice Updated"


@pytest.mark.asyncio
async def test_deleted_event_clears_state(fake_bus):
    _users(fake_bus).messages = [_msg(1, "created", "alice", {"name": "Alice"}),
                                 _msg(2, "deleted", "alice", {})]

    async with state_reader.reading_state("alice") as (get_state, caught_up):
        await caught_up.wait()

        profile = get_state()
    assert profile is None


@pytest.mark.asyncio
async def test_events_for_other_users_are_ignored(fake_bus):
    _users(fake_bus).messages = [_msg(1, "created", "bob", {"name": "Bob"})]

    async with state_reader.reading_state("alice") as (get_state, caught_up):
        await caught_up.wait()

        profile = get_state()
    assert profile is None


@pytest.mark.asyncio
async def test_malformed_event_is_ignored(fake_bus):
    _users(fake_bus).messages = [_msg(1, "created", "alice", {"name": "Alice"}),
                                 _msg(2, "updated", "alice", {"name": 42}),
                                 _msg(3, "updated", "alice", {"name": "Alice Still"})]

    async with state_reader.reading_state("alice") as (get_state, caught_up):
        await caught_up.wait()

        profile = get_state()
    assert profile.name == "Alice Still"


@pytest.mark.asyncio
async def test_snapshot_state_is_applied(fake_bus):
    _users(fake_bus).snapshots = [(5, [{"username": "alice",
                                        "name":     "Alice From Snapshot"}])]

    async with state_reader.reading_state("alice") as (get_state, caught_up):
        await caught_up.wait()

        profile = get_state()
    assert profile.name == "Alice From Snapshot"


@pytest.mark.asyncio
async def test_events_after_snapshot_override_snapshot(fake_bus):
    _users(fake_bus).snapshots = [(5, [{"username": "alice",
                                        "name":     "Alice From Snapshot"}])]
    _users(fake_bus).messages  = [_msg(6, "updated", "alice", {"name": "Alice Updated"})]

    async with state_reader.reading_state("alice") as (get_state, caught_up):
        await caught_up.wait()

        profile = get_state()
    assert profile.name == "Alice Updated"


@pytest.mark.asyncio
async def test_snapshot_for_other_user_is_ignored(fake_bus):
    _users(fake_bus).snapshots = [(5, [{"username": "bob", "name": "Bob"}])]

    async with state_reader.reading_state("alice") as (get_state, caught_up):
        await caught_up.wait()

        profile = get_state()
    assert profile is None


@pytest.mark.asyncio
async def test_get_state_is_usable_after_context_exit(fake_bus):
    _users(fake_bus).messages = [_msg(1, "created", "alice", {"name": "Alice"})]

    async with state_reader.reading_state("alice") as (get_state, caught_up):
        await caught_up.wait()

    assert get_state().name == "Alice"

