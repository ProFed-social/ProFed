# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
from datetime import datetime, timezone
import pytest
from unittest.mock import patch
from profed import identity, mentions
from profed.components.polish_activities import update_waiting as mod
from profed.components.polish_activities import translator
from profed.components.polish_activities import storage as storage_module


NOW = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)

NOTE_URL = "https://local.test/notes/1"


def _payload(content, note_url=NOTE_URL):
    return {"username": "alice",
            "activity": {"type": "Create",
                         "actor": "https://local.test/actors/alice",
                         "object": {"type": "Note", "id": note_url, "content": content}}}


def _row(content, url=NOTE_URL, object_id="act1", event_type="Create"):
    return {"url": url,
            "event_type": event_type,
            "object_id": object_id,
            "payload": json.dumps(_payload(content, url)),
            "emitted_at": NOW}


class FakeStorage:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.held = []
        self.released = []

    async def waiting_for(self, acct):
        return self.rows

    async def hold(self, url, event_type, object_id, payload, emitted_at, accts):
        self.held.append((url, accts))

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
    return "https://r.io/ghost" if acct == "ghost@r.io" else None


def _published(fake_bus):
    return fake_bus.topic("activities").published


@pytest.mark.asyncio
async def test_a_waiting_object_is_republished_as_update(fake_bus, store):
    store.rows = [_row("hi @ghost@r.io")]

    with patch.object(translator, "_resolve_one", mentions.resolver(_known)):
        assert await mod.update_all_waiting("ghost@r.io", 42) == 1

    assert [p["event_type"] for p in _published(fake_bus)] == ["Update"]


@pytest.mark.asyncio
async def test_the_update_carries_the_resolved_mention(fake_bus, store):
    store.rows = [_row("hi @ghost@r.io")]

    with patch.object(translator, "_resolve_one", mentions.resolver(_known)):
        await mod.update_all_waiting("ghost@r.io", 42)

    tag = _published(fake_bus)[0]["payload"]["activity"]["object"]["tag"]
    assert [entry["href"] for entry in tag] == ["https://r.io/ghost"]


@pytest.mark.asyncio
async def test_the_update_keeps_the_activity_id_of_the_original(fake_bus, store):
    store.rows = [_row("hi @ghost@r.io", object_id="act7")]

    with patch.object(translator, "_resolve_one", mentions.resolver(_known)):
        await mod.update_all_waiting("ghost@r.io", 42)

    assert _published(fake_bus)[0]["object_id"] == "act7"


@pytest.mark.asyncio
async def test_every_waiting_object_gets_its_own_update(fake_bus, store):
    store.rows = [_row("hi @ghost@r.io", url="https://local.test/notes/1"),
                  _row("also @ghost@r.io", url="https://local.test/notes/2")]

    with patch.object(translator, "_resolve_one", mentions.resolver(_known)):
        assert await mod.update_all_waiting("ghost@r.io", 42) == 2

    assert len(_published(fake_bus)) == 2


@pytest.mark.asyncio
async def test_an_object_that_still_misses_someone_stays_held(fake_bus, store):
    store.rows = [_row("hi @ghost@r.io and @other@r.io")]

    with patch.object(translator, "_resolve_one", mentions.resolver(_known)):
        await mod.update_all_waiting("ghost@r.io", 42)

    assert store.held == [(NOTE_URL, ["other@r.io"])]


@pytest.mark.asyncio
async def test_a_completed_object_is_released_and_not_held_again(fake_bus, store):
    store.rows = [_row("hi @ghost@r.io")]

    with patch.object(translator, "_resolve_one", mentions.resolver(_known)):
        await mod.update_all_waiting("ghost@r.io", 42)

    assert store.released == [NOTE_URL]
    assert store.held == []


@pytest.mark.asyncio
async def test_an_object_that_still_misses_someone_is_released_before_it_is_held(fake_bus, store):
    store.rows = [_row("hi @ghost@r.io and @other@r.io")]

    with patch.object(translator, "_resolve_one", mentions.resolver(_known)):
        await mod.update_all_waiting("ghost@r.io", 42)

    assert store.released == [NOTE_URL]


@pytest.mark.asyncio
async def test_without_waiting_objects_nothing_is_published(fake_bus, store):
    assert await mod.update_all_waiting("ghost@r.io", 42) == 0
    assert _published(fake_bus) == []


@pytest.mark.asyncio
async def test_two_objects_do_not_share_their_message_id(fake_bus, store):
    store.rows = [_row("hi @ghost@r.io", url="https://local.test/notes/1"),
                  _row("also @ghost@r.io", url="https://local.test/notes/2")]

    with patch.object(translator, "_resolve_one", mentions.resolver(_known)):
        await mod.update_all_waiting("ghost@r.io", 42)

    assert len(_published(fake_bus)) == 2

