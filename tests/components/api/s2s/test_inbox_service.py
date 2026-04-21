# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, Mock
from profed.core import message_bus
from profed.components.api.s2s.inbox import storage as storage_module
from profed.components.api.s2s.inbox.service import accept_inbox_activity


class FakePublishContext:
    def __init__(self): self.published = []

    async def __aenter__(self):
        async def pub(msg, **_): self.published.append(msg)
        return pub

    async def __aexit__(self, *_): pass


class FakeTopic:
    def __init__(self): self._ctx = FakePublishContext()

    def publish(self): return self._ctx

    @property
    def published(self): return self._ctx.published


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
    instance = Mock()
    instance.exists = AsyncMock(return_value=True)
    storage_module.overwrite(instance)
    yield instance
    storage_module.overwrite(None)


ACTIVITY = {"type":  "Follow",
            "actor": "https://mastodon.social/users/alice",
            "object": "https://example.com/actors/cdonat"}


@pytest.mark.asyncio
async def test_publishes_event_with_type_and_payload(fake_bus, fake_storage):
    await accept_inbox_activity("cdonat", ACTIVITY)
    
    published = fake_bus.topic("incoming_activities").published
    
    assert len(published) == 1
    assert published[0]["type"] == "incoming"
    assert published[0]["payload"]["username"] == "cdonat"
    assert published[0]["payload"]["activity"] == ACTIVITY


@pytest.mark.asyncio
async def test_returns_false_for_unknown_user(fake_bus, fake_storage):
    fake_storage.exists.return_value = False
    
    result = await accept_inbox_activity("unknown", ACTIVITY)
    
    assert result is False
    assert fake_bus.topic("incoming_activities").published == []

