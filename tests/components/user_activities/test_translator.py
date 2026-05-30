# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone
from profed.components.user_activities import translator
from profed.components.user_activities import storage as storage_module


TS = datetime(2026, 1, 1, tzinfo=timezone.utc)


class FakeStore:
    def __init__(self):
        self.rows: dict[str, dict] = {}
        self.tick = 0

    async def ensure_schema(self):
        pass

    async def upsert_created(self, username, profile, seq):
        self.rows[username] = {"created_seq": seq,
                               "last_changed_seq": seq,
                               "deleted_seq": None,
                               "profile": dict(profile)}

    async def merge_change(self, username, partial, seq):
        row = self.rows[username]
        row["profile"] = {**row["profile"], **partial}
        row["last_changed_seq"] = seq

    async def mark_deleted(self, username, seq):
        row = self.rows[username]
        row["deleted_seq"] = seq
        row["last_changed_seq"] = seq

    async def remove(self, username):
        self.rows.pop(username, None)

    async def pending_since(self, last_tick):
        return [{"username": u, **r}
                for u, r in sorted(self.rows.items(),
                                   key=lambda kv: kv[1]["last_changed_seq"])
                if r["last_changed_seq"] > last_tick]

    async def last_tick_seq(self):
        return self.tick

    async def set_last_tick_seq(self, seq):
        self.tick = seq


@pytest.fixture
def fake_store():
    backup = storage_module._instance
    storage_module._instance = FakeStore()
    yield storage_module._instance
    storage_module._instance = backup


def _msg(seq, event_type, object_id, payload):
    return (seq, event_type, object_id, TS, payload)


def _activities(fake_bus):
    return fake_bus.topic("activities").published


@pytest.mark.asyncio
async def test_created_then_tick_emits_create(fake_bus, fake_store):
    fake_bus.topic("users").messages = [_msg(1, "created", "alice", {"name": "Alice"}),
                                        _msg(2, "Tick", "", {})]

    await translator.handle_user_events()

    published = _activities(fake_bus)
    assert len(published) == 1
    assert published[0]["event_type"] == "Create"
    assert published[0]["payload"]["username"] == "alice"


@pytest.mark.asyncio
async def test_changes_without_tick_emit_nothing(fake_bus, fake_store):
    fake_bus.topic("users").messages = [_msg(1, "created", "alice", {"name": "Alice"})]

    await translator.handle_user_events()

    assert _activities(fake_bus) == []
    assert fake_store.rows["alice"]["created_seq"] == 1


@pytest.mark.asyncio
async def test_create_and_edit_in_one_interval_emits_single_create(fake_bus, fake_store):
    fake_bus.topic("users").messages = [_msg(1, "created", "alice", {"name": "Alice"}),
                                        _msg(2, "profile_edited", "alice", {"name": "Alice Updated"}),
                                        _msg(3, "Tick", "", {})]

    await translator.handle_user_events()

    published = _activities(fake_bus)
    assert len(published) == 1
    assert published[0]["event_type"] == "Create"
    assert published[0]["payload"]["activity"]["object"]["name"] == "Alice Updated"


@pytest.mark.asyncio
async def test_create_then_update_across_ticks(fake_bus, fake_store):
    fake_bus.topic("users").messages = [_msg(1, "created", "alice", {"name": "Alice"}),
                                        _msg(2, "Tick", "", {}),
                                        _msg(3, "profile_edited", "alice", {"name": "Alice2"}),
                                        _msg(4, "Tick", "", {})]

    await translator.handle_user_events()

    assert [p["event_type"] for p in _activities(fake_bus)] == ["Create", "Update"]


@pytest.mark.asyncio
async def test_create_then_delete_across_ticks(fake_bus, fake_store):
    fake_bus.topic("users").messages = [_msg(1, "created", "alice", {"name": "Alice"}),
                                        _msg(2, "Tick", "", {}),
                                        _msg(3, "deleted", "alice", {}),
                                        _msg(4, "Tick", "", {})]

    await translator.handle_user_events()

    assert [p["event_type"] for p in _activities(fake_bus)] == ["Create", "Delete"]
    assert "alice" not in fake_store.rows


@pytest.mark.asyncio
async def test_create_and_delete_in_one_interval_emits_nothing(fake_bus, fake_store):
    fake_bus.topic("users").messages = [_msg(1, "created", "alice", {"name": "Alice"}),
                                        _msg(2, "deleted", "alice", {}),
                                        _msg(3, "Tick", "", {})]

    await translator.handle_user_events()

    assert _activities(fake_bus) == []
    assert "alice" not in fake_store.rows


@pytest.mark.asyncio
async def test_second_tick_without_changes_emits_nothing(fake_bus, fake_store):
    fake_bus.topic("users").messages = [_msg(1, "created", "alice", {"name": "Alice"}),
                                        _msg(2, "Tick", "", {}),
                                        _msg(3, "Tick", "", {})]

    await translator.handle_user_events()

    assert len(_activities(fake_bus)) == 1


@pytest.mark.asyncio
async def test_tick_advances_last_tick_seq(fake_bus, fake_store):
    fake_bus.topic("users").messages = [_msg(1, "created", "alice", {"name": "Alice"}),
                                        _msg(5, "Tick", "", {})]

    await translator.handle_user_events()

    assert fake_store.tick == 5

