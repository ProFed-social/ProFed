# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone
from profed.components.activity_delivery import projections
from profed.components.activity_delivery import storage as storage_module


TS = datetime(2026, 1, 1, tzinfo=timezone.utc)


class FakeStorage:
    def __init__(self):
        self.followers:  dict[tuple, None] = {}
        self.deliveries: dict[tuple, dict] = {}

    async def ensure_schema(self):
        pass

    async def add_follower(self, following, follower):
        self.followers[(following, follower)] = None

    async def remove_follower(self, following, follower):
        self.followers.pop((following, follower), None)

    async def get_followers(self, following):
        return {f for (fw, f) in self.followers if fw == following}

    async def upsert_delivery(self, payload):
        key      = (payload["activity_id"], payload["recipient"])
        existing = self.deliveries.get(key)
        if existing is None or payload["attempt"] >= existing["attempt"]:
            self.deliveries[key] = payload

    async def get_delivery_status(self, activity_id, recipient):
        return self.deliveries.get((activity_id, recipient))


@pytest.fixture
def fake_storage():
    s = FakeStorage()
    storage_module._instance = s

    yield s

    storage_module._instance = None


@pytest.mark.asyncio
async def test_follower_created_adds_to_storage(fake_bus, fake_storage):
    fake_bus.topic("followers").messages = [
            (1, "created", "bob@remote.example|alice@example.com", TS, {})]

    await projections.followers_rebuild()

    assert ("alice@example.com", "bob@remote.example") in fake_storage.followers


@pytest.mark.asyncio
async def test_follower_deleted_removes_from_storage(fake_bus, fake_storage):
    fake_bus.topic("followers").messages = [
            (1, "created", "bob@remote.example|alice@example.com", TS, {}),
            (2, "deleted", "bob@remote.example|alice@example.com", TS, {})]

    await projections.followers_rebuild()

    assert ("alice@example.com", "bob@remote.example") not in fake_storage.followers


@pytest.mark.asyncio
async def test_delivery_succeeded_upserts_to_storage(fake_bus, fake_storage):
    payload = {"attempt":          1,
               "status_code":      202,
               "retry_after":      None,
               "first_attempt_at": datetime.now(timezone.utc).isoformat()}
    fake_bus.topic("deliveries").messages = [
            (1,
             "delivery_succeeded",
             "https://example.com/act/1|bob@remote.example",
             TS,
             payload)]

    await projections.deliveries_rebuild()

    result = await projections.get_delivery_status("https://example.com/act/1",
                                                   "bob@remote.example")
    assert result["success"] is True
    assert result["attempt"] == 1


@pytest.mark.asyncio
async def test_delivery_failed_records_failure(fake_bus, fake_storage):
    payload = {"attempt":          1,
               "status_code":      500,
               "retry_after":      None,
               "first_attempt_at": datetime.now(timezone.utc).isoformat()}
    fake_bus.topic("deliveries").messages = [
            (1,
             "delivery_failed",
             "https://example.com/act/1|bob@remote.example",
             TS,
             payload)]

    await projections.deliveries_rebuild()

    result = await projections.get_delivery_status("https://example.com/act/1",
                                                   "bob@remote.example")
    assert result["success"] is False
    assert result["status_code"] == 500

