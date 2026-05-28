# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from profed.components.user_activities import translator
import profed.components.user_activities as component


def _enqueue(fake_bus,
             event_type: str  = "created",
             object_id:  str  = "alice",
             payload:    dict = None):
    fake_bus.topic("users").messages = [(1,
                                         event_type,
                                         object_id,
                                         datetime.now(timezone.utc),
                                         {} if payload is None else payload)]


@pytest.mark.asyncio
async def test_created_user_publishes_create_activity(fake_bus):
    _enqueue(fake_bus, "created", "alice", {"name": "Alice"})

    await translator.handle_user_events()

    published = fake_bus.topic("activities").published
    assert len(published) == 1
    event = published[0]
    assert event["event_type"] == "Create"
    assert event["payload"]["username"] == "alice"
    assert event["payload"]["activity"]["actor"] == "https://example.com/actors/alice"
    assert event["payload"]["activity"]["object"]["preferredUsername"] == "alice"
    assert event["payload"]["activity"]["object"]["type"] == "Person"
    assert "id"   not in event["payload"]["activity"]
    assert "type" not in event["payload"]["activity"]


@pytest.mark.asyncio
async def test_updated_user_publishes_update_activity(fake_bus):
    _enqueue(fake_bus, "updated", "alice", {"name": "Alice"})

    await translator.handle_user_events()

    published = fake_bus.topic("activities").published
    assert len(published) == 1
    assert published[0]["event_type"] == "Update"
    assert published[0]["payload"]["activity"]["actor"] == "https://example.com/actors/alice"


@pytest.mark.asyncio
async def test_deleted_user_is_ignored(fake_bus):
    _enqueue(fake_bus, "deleted", "alice", {})

    await translator.handle_user_events()

    assert fake_bus.topic("activities").published == []


@pytest.mark.asyncio
async def test_malformed_user_event_is_ignored(fake_bus):
    _enqueue(fake_bus, "created", "alice", {"name": 42})

    await translator.handle_user_events()

    assert fake_bus.topic("activities").published == []


@pytest.mark.asyncio
async def test_replay_does_not_duplicate_activities(fake_bus):
    _enqueue(fake_bus, "created", "alice", {"name": "Alice"})

    await translator.handle_user_events()
    await translator.handle_user_events()

    assert len(fake_bus.topic("activities").published) == 1


@pytest.mark.asyncio
async def test_user_activities_component_runs_translator(monkeypatch):
    fake = AsyncMock()
    monkeypatch.setattr(component, "handle_user_events", fake)

    await component.UserActivities({})

    fake.assert_awaited_once()

