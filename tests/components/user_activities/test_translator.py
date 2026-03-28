# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock

from profed.core import message_bus
from profed.components.user_activities import translator
import profed.components.user_activities as component


class FakePublishContext:
    def __init__(self, topic):
        self._topic = topic

    async def __aenter__(self):
        async def publish(message, message_id=None):
            if message_id is not None and message_id in self._topic.message_ids:
                return None

            self._topic.message_ids.add(message_id)
            self._topic.published.append((message_id, message))
            return len(self._topic.published)

        return publish

    async def __aexit__(self, exc_type, exc, tb):
        return None


class FakeTopic:
    def __init__(self):
        self.messages = []
        self.published = []
        self.message_ids = set()

    def subscribe(self,
                  subscriber: str,
                  last_seen: int = 0,
                  include_sequence_id: bool = False):
        async def generator():
            for sequence_id, event in self.messages:
                if sequence_id > last_seen:
                    yield (sequence_id, event) if include_sequence_id else event

        return generator()

    def publish(self):
        return FakePublishContext(self)


class FakeMessageBus:
    def __init__(self):
        self._topics = {}

    def topic(self, name: str):
        if name not in self._topics:
            self._topics[name] = FakeTopic()
        return self._topics[name]


@pytest.fixture
def fake_message_bus():
    backup = message_bus._instance
    message_bus._instance = FakeMessageBus()

    yield message_bus._instance

    message_bus._instance = backup


@pytest.mark.asyncio
async def test_created_user_publishes_create_activity(fake_message_bus):
    fake_message_bus.topic("users").messages = [(1,
                                                 {"type": "created",
                                                  "payload": {"username": "alice",
                                                              "name": "Alice"}})]

    await translator.handle_user_events()

    published = fake_message_bus.topic("activities").published
    assert len(published) == 1

    _, event = published[0]
    assert event["type"] == "created"
    assert event["payload"]["username"] == "alice"
    assert event["payload"]["type"] == "Create"
    assert event["payload"]["actor"] == "https://example.com/actors/alice"
    assert event["payload"]["object"]["preferredUsername"] == "alice"
    assert event["payload"]["object"]["type"] == "Person"


@pytest.mark.asyncio
async def test_updated_user_publishes_update_activity(fake_message_bus):
    fake_message_bus.topic("users").messages = [(1,
                                                 {"type": "updated",
                                                  "payload": {"username": "alice",
                                                              "name": "Alice"}})]

    await translator.handle_user_events()

    published = fake_message_bus.topic("activities").published
    assert len(published) == 1

    _, event = published[0]
    assert event["payload"]["type"] == "Update"
    assert event["payload"]["actor"] == "https://example.com/actors/alice"


@pytest.mark.asyncio
async def test_deleted_user_is_ignored(fake_message_bus):
    fake_message_bus.topic("users").messages = [(1,
                                                 {"type": "deleted",
                                                  "payload": {"username": "alice"}})]

    await translator.handle_user_events()

    assert fake_message_bus.topic("activities").published == []


@pytest.mark.asyncio
async def test_malformed_user_event_is_ignored(fake_message_bus):
    fake_message_bus.topic("users").messages = [(1,
                                                 {"type": "created",
                                                  "payload": {"name": "Alice"}})]

    await translator.handle_user_events()

    assert fake_message_bus.topic("activities").published == []


@pytest.mark.asyncio
async def test_replay_does_not_duplicate_activities(fake_message_bus):
    fake_message_bus.topic("users").messages = [(1,
                                                 {"type": "created",
                                                  "payload": {"username": "alice",
                                                              "name": "Alice"}})]

    await translator.handle_user_events()
    await translator.handle_user_events()

    assert len(fake_message_bus.topic("activities").published) == 1


@pytest.mark.asyncio
async def test_user_activities_component_runs_translator(monkeypatch):
    fake = AsyncMock()
    monkeypatch.setattr(component, "handle_user_events", fake)

    await component.UserActivities({})

    fake.assert_awaited_once()

