# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import pytest
from datetime import datetime, timezone
from profed.components.user_person import translator
from profed.components.user_person import storage as storage_module


TS  = datetime(2026, 1, 1, tzinfo=timezone.utc)
TS2 = datetime(2026, 6, 1, tzinfo=timezone.utc)


class FakeStore:
    def __init__(self):
        self.rows: dict[str, dict] = {}
        self.tick = 0

    async def ensure_schema(self):
        pass

    async def upsert_created(self, username, profile, published, seq):
        existing = self.rows.get(username)
        self.rows[username] = {"created_seq": seq,
                               "last_changed_seq": seq,
                               "deleted_seq": None,
                               "published": existing["published"] if existing else published,
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


def _msg(seq, event_type, object_id, payload, ts=TS):
    return (seq, event_type, object_id, ts, payload)


def _person(fake_bus):
    return fake_bus.topic("person").published


@pytest.mark.asyncio
async def test_created_then_tick_emits_created(fake_bus, fake_store):
    fake_bus.topic("users").messages = [_msg(1, "created", "alice", {"name": "Alice"}),
                                        _msg(2, "Tick", "", {})]

    await translator.handle_user_events()

    published = _person(fake_bus)
    assert len(published) == 1
    assert published[0]["event_type"] == "created"
    assert published[0]["object_id"] == "alice"
    assert published[0]["payload"]["preferredUsername"] == "alice"
    assert published[0]["payload"]["name"] == "Alice"


@pytest.mark.asyncio
async def test_changes_without_tick_emit_nothing(fake_bus, fake_store):
    fake_bus.topic("users").messages = [_msg(1, "created", "alice", {"name": "Alice"})]

    await translator.handle_user_events()

    assert _person(fake_bus) == []
    assert fake_store.rows["alice"]["created_seq"] == 1


@pytest.mark.asyncio
async def test_create_and_edit_in_one_interval_emits_single_created(fake_bus, fake_store):
    fake_bus.topic("users").messages = [_msg(1, "created", "alice", {"name": "Alice"}),
                                        _msg(2, "profile_edited", "alice", {"name": "Alice Updated"}),
                                        _msg(3, "Tick", "", {})]

    await translator.handle_user_events()

    published = _person(fake_bus)
    assert len(published) == 1
    assert published[0]["event_type"] == "created"
    assert published[0]["payload"]["name"] == "Alice Updated"


@pytest.mark.asyncio
async def test_create_then_update_across_ticks(fake_bus, fake_store):
    fake_bus.topic("users").messages = [_msg(1, "created", "alice", {"name": "Alice"}),
                                        _msg(2, "Tick", "", {}),
                                        _msg(3, "profile_edited", "alice", {"name": "Alice2"}),
                                        _msg(4, "Tick", "", {})]

    await translator.handle_user_events()

    assert [p["event_type"] for p in _person(fake_bus)] == ["created", "updated"]


@pytest.mark.asyncio
async def test_create_then_delete_across_ticks(fake_bus, fake_store):
    fake_bus.topic("users").messages = [_msg(1, "created", "alice", {"name": "Alice"}),
                                        _msg(2, "Tick", "", {}),
                                        _msg(3, "deleted", "alice", {}),
                                        _msg(4, "Tick", "", {})]

    await translator.handle_user_events()

    published = _person(fake_bus)
    assert [p["event_type"] for p in published] == ["created", "deleted"]
    assert published[1]["object_id"] == "alice"
    assert published[1]["payload"] == {}
    assert "alice" not in fake_store.rows


@pytest.mark.asyncio
async def test_create_and_delete_in_one_interval_emits_nothing(fake_bus, fake_store):
    fake_bus.topic("users").messages = [_msg(1, "created", "alice", {"name": "Alice"}),
                                        _msg(2, "deleted", "alice", {}),
                                        _msg(3, "Tick", "", {})]

    await translator.handle_user_events()

    assert _person(fake_bus) == []
    assert "alice" not in fake_store.rows


@pytest.mark.asyncio
async def test_second_tick_without_changes_emits_nothing(fake_bus, fake_store):
    fake_bus.topic("users").messages = [_msg(1, "created", "alice", {"name": "Alice"}),
                                        _msg(2, "Tick", "", {}),
                                        _msg(3, "Tick", "", {})]

    await translator.handle_user_events()

    assert len(_person(fake_bus)) == 1


@pytest.mark.asyncio
async def test_tick_advances_last_tick_seq(fake_bus, fake_store):
    fake_bus.topic("users").messages = [_msg(1, "created", "alice", {"name": "Alice"}),
                                        _msg(5, "Tick", "", {})]

    await translator.handle_user_events()

    assert fake_store.tick == 5


@pytest.mark.asyncio
async def test_published_set_from_created_emitted_at(fake_bus, fake_store):
    fake_bus.topic("users").messages = [_msg(1, "created", "alice", {"name": "Alice"}, ts=TS),
                                        _msg(2, "Tick", "", {})]

    await translator.handle_user_events()

    assert _person(fake_bus)[0]["payload"]["published"] == TS.isoformat()


@pytest.mark.asyncio
async def test_published_stable_across_update(fake_bus, fake_store):
    fake_bus.topic("users").messages = [_msg(1, "created", "alice", {"name": "Alice"}, ts=TS),
                                        _msg(2, "Tick", "", {}),
                                        _msg(3, "profile_edited", "alice", {"name": "A2"}, ts=TS2),
                                        _msg(4, "Tick", "", {})]

    await translator.handle_user_events()

    published = _person(fake_bus)
    assert published[1]["event_type"] == "updated"
    assert published[1]["payload"]["published"] == TS.isoformat()


@pytest.mark.asyncio
async def test_private_key_in_created_is_excluded(fake_bus, fake_store):
    fake_bus.topic("users").messages = [_msg(1, "created", "alice",
                                             {"name": "Alice",
                                              "public_key_pem": "PUBKEY",
                                              "private_key_pem": "PRIVKEY"}),
                                        _msg(2, "Tick", "", {})]

    await translator.handle_user_events()

    payload = _person(fake_bus)[0]["payload"]
    assert payload["publicKey"]["publicKeyPem"] == "PUBKEY"
    serialized = json.dumps(payload)
    assert "PRIVKEY" not in serialized
    assert "private_key_pem" not in serialized
    assert "private_key_pem" not in fake_store.rows["alice"]["profile"]


@pytest.mark.asyncio
async def test_private_key_from_keys_generated_is_excluded(fake_bus, fake_store):
    fake_bus.topic("users").messages = [_msg(1, "created", "alice", {"name": "Alice"}),
                                        _msg(2, "keys_generated", "alice",
                                             {"public_key_pem": "PUBKEY",
                                              "private_key_pem": "PRIVKEY"}),
                                        _msg(3, "Tick", "", {})]

    await translator.handle_user_events()

    payload = _person(fake_bus)[0]["payload"]
    assert payload["publicKey"]["publicKeyPem"] == "PUBKEY"
    assert "PRIVKEY" not in json.dumps(payload)
    assert "private_key_pem" not in fake_store.rows["alice"]["profile"]


@pytest.mark.asyncio
async def test_resume_reaches_person_after_cv_changed(fake_bus, fake_store):
    fake_bus.topic("users").messages = [_msg(1, "created", "alice", {"name": "Alice"}),
                                        _msg(2, "Tick", "", {}),
                                        _msg(3, "cv_changed", "alice",
                                             {"resume": {"projects": [{"name": "Demo"}]}}),
                                        _msg(4, "Tick", "", {})]

    await translator.handle_user_events()

    published = _person(fake_bus)
    assert published[1]["event_type"] == "updated"
    assert published[1]["payload"]["resume"]["projects"] == [{"name": "Demo"}]


@pytest.mark.asyncio
async def test_updated_merges_sanitised_profile_without_private_key(fake_bus, fake_store):
    fake_bus.topic("users").messages = [_msg(1, "created", "alice", {"name": "Alice",
                                                                     "summary": "<p>x</p>"}),
                                        _msg(2, "Tick", "", {}),
                                        _msg(3, "updated", "alice", {"name": "Alice",
                                                                     "summary": "clean",
                                                                     "private_key_pem": "PRIV"}),
                                        _msg(4, "Tick", "", {})]

    await translator.handle_user_events()

    published = _person(fake_bus)
    assert published[-1]["event_type"] == "updated"
    assert published[-1]["payload"]["summary"] == "clean"
    assert "private_key_pem" not in fake_store.rows["alice"]["profile"]

