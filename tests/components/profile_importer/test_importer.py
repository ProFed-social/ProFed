# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import asyncio
import pytest
from unittest.mock import AsyncMock, patch
 
import httpx
 
from profed.core import message_bus
from profed.components.profile_importer import importer


class FakeMessageBus:
    def __init__(self):
        self._topics = {}
 
    def topic(self, name):
        if name not in self._topics:
            self._topics[name] = FakeTopic()
        return self._topics[name]
 

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
        self.messages = []
        self.published = []
        self._last_snapshot = (0, [])
 
    async def last_snapshot(self):
        return self._last_snapshot
 
    def subscribe(self,
                  subscriber,
                  last_seen=0,
                  include_sequence_id=False,
                  caught_up=None):
        async def generator():
            for seq, event in self.messages:
                if seq > last_seen:
                    yield event
            if caught_up is not None:
                caught_up.set()
            await asyncio.sleep(10_000)
        return generator()
 
    def publish(self):
        return FakePublishContext(self)
 
 
@pytest.fixture
def fake_bus():
    backup = message_bus._instance
    message_bus._instance = FakeMessageBus()
    yield message_bus._instance
    message_bus._instance = backup
 
 
def _users(fake_bus):
    return fake_bus.topic("users")
 
 
def _mf2(name):
    return {"items": [{"type": ["h-card"],
                       "properties": {"name": [name]}}]}


@pytest.mark.asyncio
async def test_new_profile_publishes_created(fake_bus):
    with patch.object(importer, "fetch_mf2", new=AsyncMock(return_value=_mf2("Alice"))):
        await importer.run_import("alice", "https://example.com/alice")
 
    published = _users(fake_bus).published
    assert len(published) == 1
    assert published[0]["type"] == "created"
    assert published[0]["payload"]["username"] == "alice"
    assert published[0]["payload"]["name"] == "Alice"


@pytest.mark.asyncio
async def test_changed_profile_publishes_updated(fake_bus):
    _users(fake_bus).messages = [(1, {"type": "created",
                                      "payload": {"username": "alice",
                                                  "name": "Alice"}})]
    with patch.object(importer, "fetch_mf2",
                      new=AsyncMock(return_value=_mf2("Alice Renamed"))):
        await importer.run_import("alice", "https://example.com/alice")
 
    published = _users(fake_bus).published
    assert len(published) == 1
    assert published[0]["type"] == "updated"
    assert published[0]["payload"]["name"] == "Alice Renamed"


@pytest.mark.asyncio
async def test_unchanged_profile_publishes_nothing(fake_bus):
    _users(fake_bus).messages = [(1, {"type": "created",
                                      "payload": {"username": "alice",
                                                  "name": "Alice"}}) ]
    with patch.object(importer, "fetch_mf2", new=AsyncMock(return_value=_mf2("Alice"))):
        await importer.run_import("alice", "https://example.com/alice")
    assert _users(fake_bus).published == []


@pytest.mark.asyncio
async def test_fetch_error_publishes_nothing(fake_bus):
    with patch.object(importer, "fetch_mf2",
                      new=AsyncMock(side_effect=httpx.HTTPStatusError("404", request=None, response=None))):
        await importer.run_import("alice", "https://example.com/alice")
    assert _users(fake_bus).published == []
 
 
@pytest.mark.asyncio
async def test_no_mf2_content_publishes_nothing(fake_bus):
    empty_mf2 = {"items": []}
    with patch.object(importer, "fetch_mf2", new=AsyncMock(return_value=empty_mf2)):
        await importer.run_import("alice", "https://example.com/alice")
    assert _users(fake_bus).published == []


@pytest.mark.asyncio
async def test_profile_importer_component_calls_run_import(fake_bus):
    from profed.components import profile_importer as component
    with patch.object(component, "run_import", new=AsyncMock()) as mock_run:
        await component.ProfileImporter({"username": "alice",
                                         "url": "https://example.com/alice"})
        mock_run.assert_awaited_once_with("alice", "https://example.com/alice")
 
 
@pytest.mark.asyncio
async def test_profile_importer_raises_without_username(fake_bus):
    from profed.components import profile_importer as component
    with pytest.raises(ValueError, match="username"):
        await component.ProfileImporter({"url": "https://example.com/alice"})
 
 
@pytest.mark.asyncio
async def test_profile_importer_raises_without_url(fake_bus):
    from profed.components import profile_importer as component
    with pytest.raises(ValueError, match="url"):
        await component.ProfileImporter({"username": "alice"})

