# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone
from profed.components.delivery_splitter import projections
from profed.components.delivery_splitter import storage as storage_module


AT = datetime(2026, 4, 1, tzinfo=timezone.utc)


class FakeStorage:
    def __init__(self):
        self.edges: dict[tuple, tuple] = {}

    async def ensure_schema(self):
        pass

    async def accept_edge(self, following, follower, at):
        self.edges[(following, follower)] = (at, None)

    async def delete_edge(self, following, follower, at):
        if (following, follower) in self.edges:
            accepted_at, _ = self.edges[(following, follower)]
            self.edges[(following, follower)] = (accepted_at, at)

    async def recipients_at(self, following, at):
        return {follower
                for (target, follower), (accepted_at, deleted_at) in self.edges.items()
                if target == following
                and accepted_at <= at
                and (deleted_at is None or deleted_at > at)}


@pytest.fixture
def fake_storage():
    backup = storage_module._instance
    storage_module._instance = FakeStorage()
    yield storage_module._instance
    storage_module._instance = backup


@pytest.mark.asyncio
async def test_accepted_records_edge(fake_storage):
    await projections._accepted("bob@remote.example|alice@example.com", {}, AT)
    assert fake_storage.edges[("alice@example.com", "bob@remote.example")] == (AT, None)


@pytest.mark.asyncio
async def test_deleted_sets_deleted_at(fake_storage):
    await projections._accepted("bob@remote.example|alice@example.com", {}, AT)
    later = datetime(2026, 5, 1, tzinfo=timezone.utc)
    await projections._deleted("bob@remote.example|alice@example.com", {}, later)
    assert fake_storage.edges[("alice@example.com", "bob@remote.example")] == (AT, later)


@pytest.mark.asyncio
async def test_recipients_at_excludes_edge_accepted_after_t(fake_storage):
    await projections._accepted("bob@remote.example|alice@example.com", {}, AT)
    before = datetime(2026, 3, 1, tzinfo=timezone.utc)
    assert await projections.recipients_at("alice@example.com", before) == set()


@pytest.mark.asyncio
async def test_recipients_at_includes_open_edge(fake_storage):
    await projections._accepted("bob@remote.example|alice@example.com", {}, AT)
    later = datetime(2026, 6, 1, tzinfo=timezone.utc)
    assert await projections.recipients_at("alice@example.com", later) == {"bob@remote.example"}


@pytest.mark.asyncio
async def test_recipients_at_excludes_edge_deleted_before_t(fake_storage):
    await projections._accepted("bob@remote.example|alice@example.com", {}, AT)
    await projections._deleted("bob@remote.example|alice@example.com", {},
                               datetime(2026, 5, 1, tzinfo=timezone.utc))
    after_delete = datetime(2026, 6, 1, tzinfo=timezone.utc)
    assert await projections.recipients_at("alice@example.com", after_delete) == set()


@pytest.mark.asyncio
async def test_followers_rebuild_signals_rebuild_finished(fake_storage, fake_bus):
    fake_storage.rebuild_finished = MagicMock()
    fake_bus.topic("followers").messages = []
    await projections.followers_rebuild()
    fake_storage.rebuild_finished.assert_called_once()

