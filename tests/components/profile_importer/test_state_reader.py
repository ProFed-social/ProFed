# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import asyncio
import pytest
 
from profed.core import message_bus
from profed.components.profile_importer import state_reader

class FakeLastSnapshot:
    def __init__(self, event_id=0, items=None):
        self._event_id = event_id
        self._items = items or []
 
    async def __call__(self):
        return self._event_id, self._items
 
 
class FakeTopic:
    def __init__(self):
        self.messages = []
        self._last_snapshot = FakeLastSnapshot()
 
    def last_snapshot(self):
        return self._last_snapshot()
 
    def subscribe(self,
                  subscriber: str,
                  last_seen: int = 0,
                  include_sequence_id: bool = False,
                  caught_up: asyncio.Event = None):
        async def generator():
            for seq, event in self.messages:
                if seq > last_seen:
                    yield event
            if caught_up is not None:
                caught_up.set()
            await asyncio.sleep(10_000)  # cancelled by context exit
        return generator()
 
 
class FakeMessageBus:
    def __init__(self):
        self._topics = {}
 
    def topic(self, name: str):
        if name not in self._topics:
            self._topics[name] = FakeTopic()
        return self._topics[name]
 
 
@pytest.fixture
def fake_bus():
    backup = message_bus._instance
    message_bus._instance = FakeMessageBus()
    yield message_bus._instance
    message_bus._instance = backup
 
 
def _users(fake_bus):
    return fake_bus.topic("users")


@pytest.mark.asyncio
async def test_no_state_returns_none(fake_bus):
    async with state_reader.reading_state("alice") as (get_state, caught_up):
        await caught_up.wait()
        assert get_state() is None


@pytest.mark.asyncio
async def test_created_event_sets_state(fake_bus):
    _users(fake_bus).messages = [(1, {"type": "created",
                                      "payload": {"username": "alice",
                                                  "name": "Alice"}})]
    async with state_reader.reading_state("alice") as (get_state, caught_up):
        await caught_up.wait()
        profile = get_state()
    assert profile is not None
    assert profile.username == "alice"
    assert profile.name == "Alice"
 
 
@pytest.mark.asyncio
async def test_updated_event_replaces_state(fake_bus):
    _users(fake_bus).messages = [(1, {"type": "created",
                                      "payload": {"username": "alice",
                                                  "name": "Alice"}}),
                                 (2, {"type": "updated",
                                      "payload": {"username": "alice",
                                                  "name": "Alice Updated"}})]
    async with state_reader.reading_state("alice") as (get_state, caught_up):
        await caught_up.wait()
        profile = get_state()
    assert profile.name == "Alice Updated"
 
 
@pytest.mark.asyncio
async def test_deleted_event_clears_state(fake_bus):
    _users(fake_bus).messages = [(1, {"type": "created",
                                      "payload": {"username": "alice",
                                                  "name": "Alice"}}),
                                 (2, {"type": "deleted",
                                      "payload": {"username": "alice"}})]
    async with state_reader.reading_state("alice") as (get_state, caught_up):
        await caught_up.wait()
        profile = get_state()
    assert profile is None
 
 
@pytest.mark.asyncio
async def test_events_for_other_users_are_ignored(fake_bus):
    _users(fake_bus).messages = [(1, {"type": "created",
                                      "payload": {"username": "bob",
                                                  "name": "Bob"}})]
    async with state_reader.reading_state("alice") as (get_state, caught_up):
        await caught_up.wait()
        profile = get_state()
    assert profile is None
 
 
@pytest.mark.asyncio
async def test_malformed_event_is_ignored(fake_bus):
    _users(fake_bus).messages = [(1, {"type": "created",
                                      "payload": {"username": "alice",
                                                  "name": "Alice"}}),
                                 (2, {"type": "updated"}),   # missing payload
                                 (3, {"type": "updated",
                                      "payload": {"username": "alice",
                                                  "name": "Alice Still"}})]
    async with state_reader.reading_state("alice") as (get_state, caught_up):
        await caught_up.wait()
        profile = get_state()
    assert profile.name == "Alice Still"


@pytest.mark.asyncio
async def test_snapshot_state_is_applied(fake_bus):
    _users(fake_bus)._last_snapshot = FakeLastSnapshot(event_id=5,
                                                       items=[{"username": "alice",
                                                               "name": "Alice From Snapshot"}])
    async with state_reader.reading_state("alice") as (get_state, caught_up):
        await caught_up.wait()
        profile = get_state()
    assert profile.name == "Alice From Snapshot"
 
 
@pytest.mark.asyncio
async def test_events_after_snapshot_override_snapshot(fake_bus):
    _users(fake_bus)._last_snapshot = FakeLastSnapshot(event_id=5,
                                                       items=[{"username": "alice",
                                                               "name": "Alice From Snapshot"}])
    _users(fake_bus).messages = [(6, {"type": "updated",
                                      "payload": {"username": "alice",
                                                  "name": "Alice Updated"}})]
    async with state_reader.reading_state("alice") as (get_state, caught_up):
        await caught_up.wait()
        profile = get_state()
    assert profile.name == "Alice Updated"
 
 
@pytest.mark.asyncio
async def test_snapshot_for_other_user_is_ignored(fake_bus):
    _users(fake_bus)._last_snapshot = FakeLastSnapshot(event_id=5,
                                                       items=[{"username": "bob",
                                                               "name": "Bob"}])
    async with state_reader.reading_state("alice") as (get_state, caught_up):
        await caught_up.wait()
        profile = get_state()
    assert profile is None


@pytest.mark.asyncio
async def test_get_state_is_usable_after_context_exit(fake_bus):
    _users(fake_bus).messages = [(1, {"type": "created",
                                      "payload": {"username": "alice",
                                                  "name": "Alice"}})]
    async with state_reader.reading_state("alice") as (get_state, caught_up):
        await caught_up.wait()
        pass
    assert get_state().name == "Alice"

