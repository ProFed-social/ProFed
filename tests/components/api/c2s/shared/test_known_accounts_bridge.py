# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone
from profed.core.message_bus.source_key import source_key
from profed.identity import account_id, acct_from_username
from profed.components.api.c2s.shared.known_accounts import bridge
from profed.components.api.c2s.shared.known_accounts import bridge_storage as storage_module


TS = datetime(2026, 1, 1, tzinfo=timezone.utc)
TS2 = datetime(2026, 6, 1, tzinfo=timezone.utc)
_USERS = source_key("users")


class FakeBridgeStore:
    def __init__(self):
        self.rows = {}

    async def ensure_schema(self):
        pass

    async def upsert_created(self, username, profile, created_at):
        self.rows[username] = {"created_at": created_at, "profile": dict(profile)}

    async def merge_change(self, username, partial):
        self.rows[username]["profile"] = {**self.rows[username]["profile"], **partial}

    async def delete(self, username):
        self.rows.pop(username, None)

    async def fetch(self, username):
        if username not in self.rows:
            return None
        return {"username": username, **self.rows[username]}


@pytest.fixture
def fake_store():
    backup = storage_module._instance
    storage_module._instance = FakeBridgeStore()
    yield storage_module._instance
    storage_module._instance = backup


def _msg(seq, event_type, object_id, payload, ts=TS):
    return (seq, event_type, object_id, ts, payload)


def _known(fake_bus):
    return fake_bus.topic("known_accounts")


@pytest.mark.asyncio
async def test_created_publishes_discovered_with_created_at(fake_bus, fake_store):
    fake_bus.topic("users").messages = [_msg(1, "created", "alice", {"name": "Alice"})]

    await bridge.handle_events()

    published = _known(fake_bus).published
    assert len(published) == 1
    event = published[0]
    assert event["event_type"] == "discovered"
    assert event["object_id"] == str(int(account_id(acct_from_username("alice"))))
    assert event["payload"]["acct"] == "alice@example.com"
    assert event["payload"]["created_at"] == TS.isoformat()
    assert event["payload"]["actor_data"]["name"] == "Alice"
    assert event["payload"]["actor_data"]["type"] == "Person"
    assert _USERS.message_id(1) in _known(fake_bus)._published_ids


@pytest.mark.asyncio
async def test_profile_edit_keeps_created_at_and_reflects_change(fake_bus, fake_store):
    fake_bus.topic("users").messages = [
        _msg(1, "created", "alice", {"name": "Alice"}, ts=TS),
        _msg(2, "profile_edited", "alice", {"name": "Alice Cooper"}, ts=TS2)]

    await bridge.handle_events()

    published = _known(fake_bus).published
    assert len(published) == 2
    assert published[0]["payload"]["created_at"] == TS.isoformat()
    assert published[1]["payload"]["created_at"] == TS.isoformat()
    assert published[1]["payload"]["actor_data"]["name"] == "Alice Cooper"
    assert _USERS.message_id(2) in _known(fake_bus)._published_ids


@pytest.mark.asyncio
async def test_publish_is_idempotent_by_message_id(fake_bus, fake_store):
    fake_bus.topic("users").messages = [_msg(1, "created", "alice", {"name": "Alice"})]
    await bridge.handle_events()
    await bridge._publish("alice", 1)

    assert len(_known(fake_bus).published) == 1

