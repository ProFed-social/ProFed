# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, Mock, patch
from profed.core import message_bus
from profed.components.accept_handler import handler
import profed.components.accept_handler.storage as storage_module


class FakePublishContext:
    def __init__(self, topic):
        self._topic = topic

    async def __aenter__(self):
        async def publish(message, message_id=None):
            self._topic.published.append(message)
        return publish

    async def __aexit__(self, exc_type, exc, tb):
        pass


class FakeTopic:
    def __init__(self):
        self.messages  = []
        self.published = []

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

    def publish(self):
        return FakePublishContext(self)


class FakeMessageBus:
    def __init__(self):
        self._topics = {}

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
    backup = storage_module._instance
    storage_module._instance = Mock()
    storage_module._instance.get_by_actor_url = AsyncMock(return_value=123456)
    yield storage_module._instance
    storage_module._instance = backup


ACCEPT_ACTIVITY = {
    "id":     "https://remote.example/activities/1",
    "type":   "Accept",
    "actor":  "https://remote.example/actors/bob",
    "object": {"id":     "https://example.com/actors/alice#follows/123456",
               "type":   "Follow",
               "actor":  "https://example.com/actors/alice",
               "object": "https://remote.example/actors/bob"}}


@pytest.mark.asyncio
async def test_accept_publishes_follow_accepted(fake_bus, fake_storage):
    fake_bus.topic("incoming_activities").messages = \
        [(1, {"type":    "incoming",
              "payload": {"username": "alice",
                          "activity": ACCEPT_ACTIVITY}})]

    with patch("profed.components.accept_handler.handler.actor_url_from_username",
               return_value="https://example.com/actors/alice"):
        await handler.handle_incoming_activities()

    published = fake_bus.topic("known_accounts").published
    assert len(published) == 1
    assert published[0]["type"] == "follow_accepted"
    assert published[0]["payload"]["account_id"] == 123456
    assert published[0]["payload"]["following_user"] == "alice"


@pytest.mark.asyncio
async def test_accept_for_other_user_is_ignored(fake_bus, fake_storage):
    fake_bus.topic("incoming_activities").messages = \
        [(1, {"type":    "incoming",
              "payload": {"username": "alice",
                          "activity": ACCEPT_ACTIVITY}})]

    with patch("profed.components.accept_handler.handler.actor_url_from_username",
               return_value="https://example.com/actors/bob"):
        await handler.handle_incoming_activities()

    assert fake_bus.topic("known_accounts").published == []


@pytest.mark.asyncio
async def test_accept_unknown_actor_is_ignored(fake_bus, fake_storage):
    storage_module._instance.get_by_actor_url = AsyncMock(return_value=None)
    fake_bus.topic("incoming_activities").messages = \
        [(1, {"type":    "incoming",
              "payload": {"username": "alice",
                          "activity": ACCEPT_ACTIVITY}})]

    with patch("profed.components.accept_handler.handler.actor_url_from_username",
               return_value="https://example.com/actors/alice"):
        await handler.handle_incoming_activities()

    assert fake_bus.topic("known_accounts").published == []


@pytest.mark.asyncio
async def test_invalid_accept_is_ignored(fake_bus, fake_storage):
    fake_bus.topic("incoming_activities").messages = \
        [(1, {"type":    "incoming",
              "payload": {"username": "alice",
                          "activity": {"type": "Accept"}}})]

    await handler.handle_incoming_activities()

    assert fake_bus.topic("known_accounts").published == []


@pytest.mark.asyncio
async def test_non_accept_activity_is_ignored(fake_bus, fake_storage):
    fake_bus.topic("incoming_activities").messages = \
        [(1, {"type":    "incoming",
              "payload": {"username": "alice",
                          "activity": {"type":   "Like",
                                       "actor":  "https://remote.example/actors/bob",
                                       "object": "https://example.com/notes/1"}}})]

    await handler.handle_incoming_activities()

    assert fake_bus.topic("known_accounts").published == []

