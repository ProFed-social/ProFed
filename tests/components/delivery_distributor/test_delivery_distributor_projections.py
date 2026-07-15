# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone
from profed.components.delivery_distributor import projections
from profed.components.delivery_distributor import storage as storage_module


AT = datetime(2026, 4, 1, tzinfo=timezone.utc)


class FakeStorage:
    def __init__(self):
        self.calls: list[tuple] = []

    async def enqueue(self, *a):
        self.calls.append(("enqueue", a))

    async def mark_attempting(self, *a):
        self.calls.append(("mark_attempting", a))

    async def mark_failed(self, *a):
        self.calls.append(("mark_failed", a))

    async def dequeue(self, *a):
        self.calls.append(("dequeue", a))

    async def upsert_user_key(self, *a):
        self.calls.append(("upsert_user_key", a))


@pytest.fixture
def fake_storage():
    backup = storage_module._instance
    storage_module._instance = FakeStorage()
    yield storage_module._instance
    storage_module._instance = backup


@pytest.mark.asyncio
async def test_queued_enqueues(fake_storage):
    await projections._queued("https://x/1|bob@r",
                              {"username": "alice", "activity": {"type": "Create"}}, AT, 42)
    assert ("enqueue", ("bob@r", "https://x/1", 42, "alice", {"type": "Create"})) in fake_storage.calls


@pytest.mark.asyncio
async def test_attempting_marks(fake_storage):
    await projections._attempting("https://x/1|bob@r", {"attempt": 2}, AT, 43)
    assert ("mark_attempting", ("bob@r", "https://x/1", 2, AT)) in fake_storage.calls


@pytest.mark.asyncio
async def test_failed_marks(fake_storage):
    await projections._failed("https://x/1|bob@r", {"attempt": 2}, AT, 44)
    assert ("mark_failed", ("bob@r", "https://x/1", AT)) in fake_storage.calls


@pytest.mark.asyncio
async def test_done_dequeues(fake_storage):
    await projections._removed("https://x/1|bob@r", {"attempt": 2}, AT, 45)
    assert ("dequeue", ("bob@r", "https://x/1")) in fake_storage.calls


@pytest.mark.asyncio
async def test_keys_upsert(fake_storage):
    await projections._upsert_key("alice", {"public_key_pem": "PUB", "private_key_pem": "PRIV"})
    assert ("upsert_user_key", ("alice", "PUB", "PRIV")) in fake_storage.calls


@pytest.mark.asyncio
async def test_keys_upsert_skips_incomplete(fake_storage):
    await projections._upsert_key("alice", {"public_key_pem": "PUB"})
    assert fake_storage.calls == []


@pytest.mark.asyncio
async def test_queue_rebuild_signals_rebuild_finished(fake_storage, fake_bus):
    fake_storage.rebuild_finished = MagicMock()
    fake_bus.topic("deliveries").messages = []
    await projections.queue_rebuild()
    fake_storage.rebuild_finished.assert_called_once()

