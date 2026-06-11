# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import os
import pytest
from datetime import datetime, timezone

from profed.core.config import config, raw
from profed.components.person_account import translator
import profed.components.person_account.storage as storage_module


TS = datetime(2026, 1, 1, tzinfo=timezone.utc)
ALICE_ACCT = "alice@example.com"
ALICE_ACTOR = "https://example.com/actors/alice"


@pytest.fixture
def cfg():
    backup = (raw.paths, raw.argv, os.environ)
    raw.paths = []
    raw.argv = []
    os.environ = {"PROFED_API__DOMAIN": "example.com", "PROFED_PROFED__RUN": "person_account"}
    config.reset()
    yield
    raw.paths, raw.argv, os.environ = backup


class _FakeStore:
    def __init__(self):
        self.edges = set()
        self.statuses = {}

    def rebuild_finished(self):
        pass

    async def add_edge(self, follower, following):
        if (follower, following) in self.edges:
            return False
        self.edges.add((follower, following))
        return True

    async def remove_edge(self, follower, following):
        if (follower, following) not in self.edges:
            return False
        self.edges.discard((follower, following))
        return True

    async def count_followers(self, acct):
        return sum(1 for follower, following in self.edges if following == acct)

    async def count_following(self, acct):
        return sum(1 for follower, following in self.edges if follower == acct)

    async def count_follows(self, acct):
        return (await self.count_followers(acct)), (await self.count_following(acct))

    async def bump_statuses(self, username, delta):
        self.statuses[username] = max(self.statuses.get(username, 0) + delta, 0)
        return self.statuses[username]

    async def get_statuses(self, username):
        return self.statuses.get(username, 0)


@pytest.fixture
def fake_store():
    backup = storage_module._instance
    storage_module._instance = _FakeStore()
    yield storage_module._instance
    storage_module._instance = backup


def _actor(username="alice"):
    base = f"https://example.com/actors/{username}"
    return {"@context": "https://www.w3.org/ns/activitystreams",
            "id": base,
            "type": "Person",
            "preferredUsername": username,
            "name": "Alice",
            "summary": "hi",
            "inbox": f"{base}/inbox",
            "outbox": f"{base}/outbox"}


def _msg(seq, event_type, object_id, payload, ts=TS):
    return (seq, event_type, object_id, ts, payload)


def _accounts(fake_bus):
    return fake_bus.topic("accounts").published


def _follower_edge(name):
    return f"{name}@remote.example|{ALICE_ACCT}"


def _following_edge(name):
    return f"{ALICE_ACCT}|{name}@remote.example"


def _local_follow_edge(name):
    return f"{ALICE_ACCT}|{name}@example.com"


def _status_create(note_id="https://example.com/notes/1"):
    return {"username": "alice",
            "activity": {"actor": ALICE_ACTOR,
                         "object": {"id": note_id, "type": "Note"}}}


def _status_announce(boosted="https://remote.example/notes/9"):
    return {"username": "alice",
            "activity": {"actor": ALICE_ACTOR, "object": boosted}}


def _status_delete(note_id="https://example.com/notes/1"):
    return {"username": "alice",
            "activity": {"actor": ALICE_ACTOR, "object": note_id}}


def _actor_create():
    return {"username": "alice",
            "activity": {"actor": ALICE_ACTOR,
                         "object": {"id": ALICE_ACTOR, "type": "Person"}}}


def _actor_self_delete():
    return {"username": "alice",
            "activity": {"actor": ALICE_ACTOR, "object": ALICE_ACTOR}}


@pytest.mark.asyncio
async def test_person_created_emits_account(fake_bus, fake_store, cfg):
    fake_bus.topic("person").messages = [_msg(1, "created", "alice", _actor())]

    await translator.handle_person_events()

    published = _accounts(fake_bus)
    assert len(published) == 1
    assert published[0]["event_type"] == "created"
    assert published[0]["object_id"] == "alice"
    acc = published[0]["payload"]
    assert acc["username"] == "alice"
    assert acc["acct"] == ALICE_ACCT
    assert acc["display_name"] == "Alice"
    assert acc["url"] == ALICE_ACTOR
    assert acc["followers_count"] == 0
    assert acc["following_count"] == 0
    assert acc["statuses_count"] == 0


@pytest.mark.asyncio
async def test_created_reflects_existing_follower_edges(fake_bus, fake_store, cfg):
    await fake_store.add_edge("bob@remote.example", ALICE_ACCT)
    await fake_store.add_edge("carol@remote.example", ALICE_ACCT)
    fake_bus.topic("person").messages = [_msg(5, "created", "alice", _actor())]

    await translator.handle_person_events()

    assert _accounts(fake_bus)[0]["payload"]["followers_count"] == 2


@pytest.mark.asyncio
async def test_created_reflects_existing_following_edges(fake_bus, fake_store, cfg):
    await fake_store.add_edge(ALICE_ACCT, "bob@remote.example")
    await fake_store.add_edge(ALICE_ACCT, "carol@remote.example")
    fake_bus.topic("person").messages = [_msg(5, "created", "alice", _actor())]

    await translator.handle_person_events()

    assert _accounts(fake_bus)[0]["payload"]["following_count"] == 2


@pytest.mark.asyncio
async def test_created_at_from_published(fake_bus, fake_store, cfg):
    actor = {**_actor(), "published": "2026-01-01T00:00:00+00:00"}
    fake_bus.topic("person").messages = [_msg(1, "created", "alice", actor)]

    await translator.handle_person_events()

    assert _accounts(fake_bus)[0]["payload"]["created_at"] == "2026-01-01T00:00:00+00:00"


@pytest.mark.asyncio
async def test_person_updated_emits_updated_account(fake_bus, fake_store, cfg):
    fake_bus.topic("person").messages = [_msg(1, "updated", "alice", _actor())]

    await translator.handle_person_events()

    published = _accounts(fake_bus)
    assert [p["event_type"] for p in published] == ["updated"]
    assert published[0]["payload"]["username"] == "alice"


@pytest.mark.asyncio
async def test_person_deleted_emits_deleted(fake_bus, fake_store, cfg):
    fake_bus.topic("person").messages = [_msg(1, "deleted", "alice", {})]

    await translator.handle_person_events()

    published = _accounts(fake_bus)
    assert [p["event_type"] for p in published] == ["deleted"]
    assert published[0]["payload"] == {}


@pytest.mark.asyncio
async def test_accepted_follower_emits_followers_changed(fake_bus, fake_store, cfg):
    fake_bus.topic("followers").messages = [_msg(1, "accepted", _follower_edge("bob"), {})]

    await translator.handle_followers_events()

    published = _accounts(fake_bus)
    assert len(published) == 1
    assert published[0]["event_type"] == "followers_changed"
    assert published[0]["object_id"] == "alice"
    assert published[0]["payload"]["count"] == 1


@pytest.mark.asyncio
async def test_followers_changed_tracks_count(fake_bus, fake_store, cfg):
    fake_bus.topic("followers").messages = [
        _msg(1, "accepted", _follower_edge("bob"), {}),
        _msg(2, "accepted", _follower_edge("carol"), {}),
        _msg(3, "deleted", _follower_edge("bob"), {})]

    await translator.handle_followers_events()

    published = _accounts(fake_bus)
    assert all(p["event_type"] == "followers_changed" for p in published)
    assert all(p["object_id"] == "alice" for p in published)
    assert [p["payload"]["count"] for p in published] == [1, 2, 1]


@pytest.mark.asyncio
async def test_deleting_unknown_edge_emits_nothing(fake_bus, fake_store, cfg):
    fake_bus.topic("followers").messages = [_msg(1, "deleted", _follower_edge("dan"), {})]

    await translator.handle_followers_events()

    assert _accounts(fake_bus) == []


@pytest.mark.asyncio
async def test_requested_is_ignored(fake_bus, fake_store, cfg):
    fake_bus.topic("followers").messages = [_msg(1, "requested", _follower_edge("bob"), {})]

    await translator.handle_followers_events()

    assert _accounts(fake_bus) == []


@pytest.mark.asyncio
async def test_rejected_is_ignored(fake_bus, fake_store, cfg):
    fake_bus.topic("followers").messages = [_msg(1, "rejected", _following_edge("bob"), {})]

    await translator.handle_followers_events()

    assert _accounts(fake_bus) == []


@pytest.mark.asyncio
async def test_duplicate_accept_emits_once(fake_bus, fake_store, cfg):
    fake_bus.topic("followers").messages = [
        _msg(1, "accepted", _follower_edge("bob"), {}),
        _msg(2, "accepted", _follower_edge("bob"), {})]

    await translator.handle_followers_events()

    assert [p["payload"]["count"] for p in _accounts(fake_bus)] == [1]


@pytest.mark.asyncio
async def test_outgoing_accept_emits_following_changed(fake_bus, fake_store, cfg):
    fake_bus.topic("followers").messages = [_msg(1, "accepted", _following_edge("bob"), {})]

    await translator.handle_followers_events()

    published = _accounts(fake_bus)
    assert len(published) == 1
    assert published[0]["event_type"] == "following_changed"
    assert published[0]["object_id"] == "alice"
    assert published[0]["payload"]["count"] == 1


@pytest.mark.asyncio
async def test_local_follow_emits_both_sides(fake_bus, fake_store, cfg):
    fake_bus.topic("followers").messages = [_msg(1, "accepted", _local_follow_edge("bob"), {})]

    await translator.handle_followers_events()

    published = _accounts(fake_bus)
    emitted = {(p["event_type"], p["object_id"]) for p in published}
    assert emitted == {("followers_changed", "bob"),
                       ("following_changed", "alice")}
    assert all(p["payload"]["count"] == 1 for p in published)


@pytest.mark.asyncio
async def test_status_create_increments(fake_bus, fake_store, cfg):
    fake_bus.topic("activities").messages = [_msg(1, "Create", "n1", _status_create("n1"))]

    await translator.handle_statuses_events()

    assert _accounts(fake_bus)[0]["payload"]["count"] == 1


@pytest.mark.asyncio
async def test_status_announce_increments(fake_bus, fake_store, cfg):
    fake_bus.topic("activities").messages = [_msg(1, "Announce", "b1", _status_announce())]

    await translator.handle_statuses_events()

    assert _accounts(fake_bus)[0]["payload"]["count"] == 1


@pytest.mark.asyncio
async def test_status_delete_decrements(fake_bus, fake_store, cfg):
    await fake_store.bump_statuses("alice", 2)
    fake_bus.topic("activities").messages = [_msg(1, "Delete", "n1", _status_delete("n1"))]

    await translator.handle_statuses_events()

    assert _accounts(fake_bus)[0]["payload"]["count"] == 1


@pytest.mark.asyncio
async def test_statuses_skips_actor_create(fake_bus, fake_store, cfg):
    fake_bus.topic("activities").messages = [_msg(1, "Create", ALICE_ACTOR, _actor_create())]

    await translator.handle_statuses_events()

    assert _accounts(fake_bus) == []


@pytest.mark.asyncio
async def test_statuses_skips_actor_self_delete(fake_bus, fake_store, cfg):
    fake_bus.topic("activities").messages = [_msg(1, "Delete", ALICE_ACTOR, _actor_self_delete())]

    await translator.handle_statuses_events()

    assert _accounts(fake_bus) == []

