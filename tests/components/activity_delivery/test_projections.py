# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import pytest
from unittest.mock import AsyncMock, patch

from datetime import datetime, timezone

from profed.core import message_bus
from profed.components.activity_delivery import projections
from profed.components.activity_delivery import storage as storage_module
 
 
class FakeStorage:
    def __init__(self):
        self.followers: dict[tuple, None] = {}
        self.deliveries: dict[tuple, dict] = {}
 
    async def ensure_schema(self): pass
 
    async def add_follower(self, following, follower):
        self.followers[(following, follower)] = None
 
    async def remove_follower(self, following, follower):
        self.followers.pop((following, follower), None)
 
    async def get_followers(self, following):
        return {f for (fw, f) in self.followers if fw == following}
 
    async def upsert_delivery(self, payload):
        key = (payload["activity_id"], payload["recipient"])
        existing = self.deliveries.get(key)
        if existing is None or payload["attempt"] >= existing["attempt"]:
            self.deliveries[key] = payload
 
    async def get_delivery_status(self, activity_id, recipient):
        return self.deliveries.get((activity_id, recipient))
 
 
class FakeTopic:
    def __init__(self):
        self.messages = []
 
    async def last_snapshot(self):
        return 0, []

    def subscribe(self,
                  subscriber,
                  last_seen=0,
                  include_sequence_id=False,
                  caught_up=None):
        async def generator():
            for seq, event in self.messages:
                if seq > last_seen:
                    yield (seq, event) if include_sequence_id else event
            if caught_up is not None:
                caught_up.set()
        return generator()
 
 
class FakeMessageBus:
    def __init__(self): self._topics = {}
    def topic(self, name):
        if name not in self._topics:
            self._topics[name] = FakeTopic()
        return self._topics[name]
 
 
@pytest.fixture
def fake_bus():
    backup = message_bus._instance
    message_bus._instance = FakeMessageBus()
    yield message_bus._instance
    message_bus._instance = backup
 
 
@pytest.fixture
def fake_storage():
    s = FakeStorage()
    storage_module._instance = s
    yield s
    storage_module._instance = None
 
 
@pytest.mark.asyncio
async def test_follower_created_adds_to_storage(fake_bus, fake_storage):
    fake_bus.topic("followers").messages = [(1, {"type": "created",
                                                 "payload": {"following": "alice@example.com",
                                                             "follower": "bob@remote.example"}})]
    await projections.followers_rebuild()
    assert ("alice@example.com", "bob@remote.example") in fake_storage.followers
 
 
@pytest.mark.asyncio
async def test_follower_deleted_removes_from_storage(fake_bus, fake_storage):
    fake_bus.topic("followers").messages = [(1, {"type": "created",
                                                 "payload": {"following": "alice@example.com",
                                                             "follower": "bob@remote.example"}}),
                                            (2, {"type": "deleted",
                                                 "payload": {"following": "alice@example.com",
                                                             "follower": "bob@remote.example"}})]
    await projections.followers_rebuild()
    assert ("alice@example.com", "bob@remote.example") not in fake_storage.followers
 
 
@pytest.mark.asyncio
async def test_delivery_attempted_upserts_to_storage(fake_bus, fake_storage):
    payload = {"activity_id": "https://example.com/act/1",
               "recipient":   "bob@remote.example",
               "success":     True,
               "attempt":     1,
               "status_code": 202,
               "retry_after": None,
               "first_attempt_at": datetime.now(timezone.utc).isoformat()}
    fake_bus.topic("deliveries").messages = [(1, {"type": "attempted",
                                                  "payload": payload})]
    await projections.deliveries_rebuild()
    result = await projections.get_delivery_status("https://example.com/act/1",
                                                    "bob@remote.example")
    assert result["success"] is True

