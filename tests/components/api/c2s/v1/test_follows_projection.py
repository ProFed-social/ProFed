# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone
from profed.components.api.c2s.v1.accounts.follows import projection
from profed.components.api.c2s.v1.accounts.follows import storage as storage_module


TS = datetime(2026, 1, 1, tzinfo=timezone.utc)
FOLLOWER = "https://remote.example/actors/bob"
FOLLOWING = "https://example.com/actors/alice"
EDGE = f"{FOLLOWER}|{FOLLOWING}"


class FakeStore:
    def __init__(self):
        self.edges = {}

    async def ensure_schema(self):
        pass

    def rebuild_finished(self):
        pass

    async def upsert(self, follower, following, state, follow_activity_id=None):
        self.edges[(follower, following)] = {"state": state, "follow_activity_id": follow_activity_id}

    async def delete(self, follower, following):
        self.edges.pop((follower, following), None)


@pytest.fixture
def fake_store():
    store = FakeStore()
    storage_module._instance = store
    yield store
    storage_module._instance = None


def _msg(seq, event_type, object_id, payload):
    return (seq, event_type, object_id, TS, payload)


@pytest.mark.asyncio
async def test_requested_upserts_requested_with_activity_id(fake_bus, fake_store):
    fake_bus.topic("followers").messages = [_msg(1,
                                                 "requested",
                                                 EDGE,
                                                 {"follow_activity_id": "act-1"})]

    await projection.rebuild()

    edge = fake_store.edges[(FOLLOWER, FOLLOWING)]
    assert edge["state"] == "requested"
    assert edge["follow_activity_id"] == "act-1"


@pytest.mark.asyncio
async def test_accepted_upserts_accepted(fake_bus, fake_store):
    fake_bus.topic("followers").messages = [_msg(1, "accepted", EDGE, {})]

    await projection.rebuild()

    assert fake_store.edges[(FOLLOWER, FOLLOWING)]["state"] == "accepted"


@pytest.mark.asyncio
async def test_rejected_removes_edge(fake_bus, fake_store):
    fake_bus.topic("followers").messages = [_msg(1, "requested", EDGE, {}),
                                            _msg(2, "rejected", EDGE, {})]

    await projection.rebuild()

    assert (FOLLOWER, FOLLOWING) not in fake_store.edges


@pytest.mark.asyncio
async def test_deleted_removes_edge(fake_bus, fake_store):
    fake_bus.topic("followers").messages = [_msg(1, "accepted", EDGE, {}),
                                            _msg(2, "deleted", EDGE, {})]

    await projection.rebuild()

    assert (FOLLOWER, FOLLOWING) not in fake_store.edges


@pytest.mark.asyncio
async def test_snapshot_upserts_accepted_skips_invalid_state(fake_bus, fake_store):
    fake_bus.topic("followers").snapshots = [(0,
                                              [{"follower": FOLLOWER,
                                                "following": FOLLOWING,
                                                "state": "accepted"},
                                               {"follower": "https://remote.example/actors/carol",
                                                "following": FOLLOWING,
                                                "state": "bogus"}])]

    await projection.rebuild()

    assert (FOLLOWER, FOLLOWING) in fake_store.edges
    assert ("https://remote.example/actors/carol", FOLLOWING) not in fake_store.edges

