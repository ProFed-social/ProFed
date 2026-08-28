# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
from datetime import datetime, timezone
import pytest
from unittest.mock import patch
from profed import identity, mentions
import profed.components.polish_activities.translator as mod
from profed.components.polish_activities import storage as storage_module


NOW = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)

NOTE_URL = "https://local.test/notes/1"


def _payload(content, **overrides):
    return {"username": "alice",
            "activity": {"type": "Create",
                         "actor": "https://local.test/actors/alice",
                         "object": {"type": "Note", "id": NOTE_URL, "content": content, **overrides}}}


class FakeStorage:
    def __init__(self):
        self.held = []
        self.released = []

    async def hold(self, url, event_type, object_id, payload, emitted_at, accts):
        self.held.append({"url": url, "event_type": event_type, "object_id": object_id,
                          "payload": payload, "emitted_at": emitted_at, "accts": accts})

    async def release(self, url):
        self.released.append(url)


@pytest.fixture(autouse=True)
def store():
    backup = storage_module._instance
    storage_module._instance = FakeStorage()
    with patch.object(identity, "domain", lambda: "local.test"):
        yield storage_module._instance
    storage_module._instance = backup


async def _known(acct):
    return "https://r.io/dave" if acct == "dave@r.io" else None


def _requested(fake_bus):
    return [(p["event_type"], p["object_id"]) for p in fake_bus.topic("unknown_actors").published]


def _forwarded(fake_bus):
    return fake_bus.topic("activities").published


@pytest.mark.asyncio
async def test_a_resolvable_mention_is_not_held(fake_bus, store):
    with patch.object(mod, "_resolve_one", mentions.resolver(_known)):
        await mod._polish_and_forward("Create", "act1", _payload("hi @dave@r.io"), NOW, 7)

    assert store.held == []
    assert store.released == [NOTE_URL]


@pytest.mark.asyncio
async def test_an_unresolvable_mention_holds_the_object(fake_bus, store):
    with patch.object(mod, "_resolve_one", mentions.resolver(_known)):
        await mod._polish_and_forward("Create", "act1", _payload("hi @ghost@r.io"), NOW, 7)

    assert [entry["url"] for entry in store.held] == [NOTE_URL]
    assert store.held[0]["accts"] == ["ghost@r.io"]


@pytest.mark.asyncio
async def test_an_unresolvable_mention_is_reported(fake_bus, store):
    with patch.object(mod, "_resolve_one", mentions.resolver(_known)):
        await mod._polish_and_forward("Create", "act1", _payload("hi @ghost@r.io"), NOW, 7)

    assert _requested(fake_bus) == [("discovered_acct", "ghost@r.io")]


@pytest.mark.asyncio
async def test_only_the_unresolved_mentions_are_reported(fake_bus, store):
    with patch.object(mod, "_resolve_one", mentions.resolver(_known)):
        await mod._polish_and_forward("Create", "act1", _payload("hi @dave@r.io and @ghost@r.io"), NOW, 7)

    assert _requested(fake_bus) == [("discovered_acct", "ghost@r.io")]


@pytest.mark.asyncio
async def test_a_local_mention_is_never_reported(fake_bus, store):
    with patch.object(mod, "_resolve_one", mentions.resolver(_known)):
        await mod._polish_and_forward("Create", "act1", _payload("hi @nobody"), NOW, 7)

    assert _requested(fake_bus) == []
    assert store.held == []


@pytest.mark.asyncio
async def test_the_activity_is_forwarded_although_a_mention_is_missing(fake_bus, store):
    with patch.object(mod, "_resolve_one", mentions.resolver(_known)):
        await mod._polish_and_forward("Create", "act1", _payload("hi @ghost@r.io"), NOW, 7)

    assert len(_forwarded(fake_bus)) == 1


@pytest.mark.asyncio
async def test_the_held_payload_is_the_raw_one(fake_bus, store):
    payload = _payload("hi @dave@r.io and @ghost@r.io")
    with patch.object(mod, "_resolve_one", mentions.resolver(_known)):
        await mod._polish_and_forward("Create", "act1", payload, NOW, 7)

    held = json.loads(store.held[0]["payload"])["activity"]["object"]["content"]
    assert held == "hi @dave@r.io and @ghost@r.io"
    assert "<a" not in held


@pytest.mark.asyncio
async def test_the_held_entry_keeps_event_type_and_object_id(fake_bus, store):
    with patch.object(mod, "_resolve_one", mentions.resolver(_known)):
        await mod._polish_and_forward("Update", "act1", _payload("hi @ghost@r.io"), NOW, 7)

    assert (store.held[0]["event_type"], store.held[0]["object_id"]) == ("Update", "act1")


@pytest.mark.asyncio
async def test_a_delete_releases_the_object(fake_bus, store):
    activity = {"type": "Delete", "actor": "https://local.test/actors/alice", "object": NOTE_URL}

    await mod._deleted("Delete", "act1", {"username": "alice", "activity": activity}, NOW, 7)

    assert store.released == [NOTE_URL]


@pytest.mark.asyncio
async def test_a_delete_is_still_forwarded(fake_bus, store):
    activity = {"type": "Delete", "actor": "https://local.test/actors/alice", "object": NOTE_URL}

    await mod._deleted("Delete", "act1", {"username": "alice", "activity": activity}, NOW, 7)

    assert len(_forwarded(fake_bus)) == 1


@pytest.mark.asyncio
async def test_an_activity_without_an_object_url_is_not_held(fake_bus, store):
    payload = {"username": "alice",
               "activity": {"type": "Create", "actor": "https://local.test/actors/alice",
                            "object": {"type": "Note", "content": "hi @ghost@r.io"}}}

    with patch.object(mod, "_resolve_one", mentions.resolver(_known)):
        await mod._polish_and_forward("Create", "act1", payload, NOW, 7)

    assert store.held == []


def test_only_remote_accts_count_as_unresolved():
    resolved = [("dave", "r.io", "dave@r.io", None),
                ("nobody", None, "nobody@local.test", None),
                ("carol", "c.io", "carol@c.io", "https://c.io/carol")]

    with patch.object(identity, "domain", lambda: "local.test"):
        assert mod.unresolved_accts(resolved) == ["dave@r.io"]


def test_the_same_unresolved_acct_is_listed_once():
    resolved = [("dave", "r.io", "dave@r.io", None), ("dave", "r.io", "dave@r.io", None)]

    with patch.object(identity, "domain", lambda: "local.test"):
        assert mod.unresolved_accts(resolved) == ["dave@r.io"]

