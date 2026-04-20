# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import os
from typing import Dict
import asyncio

from profed.core.config import config, raw
from profed.core import message_bus
from profed.components.activity_delivery import handler, delivery
from profed.components.activity_delivery import storage as storage_module
 
 
class FakePublishContext:
    def __init__(self, topic):
        self._topic = topic
    async def __aenter__(self):
        async def publish(msg, message_id=None):
            self._topic.published.append(msg)
        return publish
    async def __aexit__(self, *_): pass
 
 
class FakeTopic:
    def __init__(self):
        self.messages = []
        self.published = []
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
        return generator()
    def publish(self): return FakePublishContext(self)
 
 
class FakeMessageBus:
    def __init__(self): self._topics = {}
    def topic(self, name):
        if name not in self._topics:
            self._topics[name] = FakeTopic()
        return self._topics[name]
 
 
class FakeStorage:
    async def get_followers(self, following): return {"bob@remote.example"}
    async def get_delivery_status(self, activity_id, recipient): return None
    async def upsert_delivery(self, payload): pass
 

class Cfg:
    def __init__(self, cfg: Dict[str, Dict[str, str]]):
        raw.paths = []
        raw.argv = [""] + [f"--{section}.{parameter}={value}"
                           for section, s in cfg.items()
                           for parameter, value in s.items()]
        os.environ = {k: v for k, v in os.environ.items()
                      if not k.startswith("PROFED_")}

    def __enter__(self):
        config.reset()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            raise exc_val
 
@pytest.fixture
def fake_bus():
    backup = message_bus._instance
    message_bus._instance = FakeMessageBus()
    yield message_bus._instance
    message_bus._instance = backup
 
 
@pytest.fixture
def fake_storage():
    storage_module._instance = FakeStorage()
    yield storage_module._instance
    storage_module._instance = None
 
 
ACTIVITY = {"type": "created",
            "payload": {"id": "https://example.com/act/1",
                        "username": "alice",
                        "type": "Create",
                        "actor": "https://example.com/actors/alice"}}

 
@pytest.mark.asyncio
async def test_handle_activities_creates_delivery_task(fake_bus, fake_storage):
    fake_bus.topic("activities").messages = [(1, ACTIVITY)]

    with Cfg({"profed": {"run": "activity_delivery"},
              "api":    {"domain": "example.com"}}):
        with patch.object(handler, "deliver", new=AsyncMock()) as mock_deliver, \
             patch("profed.components.activity_delivery.handler.asyncio.create_task",
                   side_effect=lambda coro, **kw: asyncio.ensure_future(coro)):
            await handler.handle_activities({"domain": "example.com"})
            await asyncio.sleep(0)  # let tasks run

            mock_deliver.assert_awaited_once()
            call_kwargs = mock_deliver.call_args
            assert call_kwargs[0][1] == "https://example.com/act/1"
            assert call_kwargs[0][3] == "bob@remote.example"
 
 
@pytest.mark.asyncio
async def test_handle_activities_missing_id_is_ignored(fake_bus, fake_storage):
    fake_bus.topic("activities").messages = [(1, {"type": "created",
                                                  "username": "alice",
                                                  "payload": {"type": "Create"}})]

    with Cfg({"profed": {"run": "activity_delivery"},
              "api":    {"domain": "example.com"}}):
        with patch.object(handler, "deliver", new=AsyncMock()) as mock_deliver, \
             patch("profed.components.activity_delivery.handler.asyncio.create_task",
                   side_effect=lambda coro, **kw: asyncio.ensure_future(coro)):
            await handler.handle_activities({"domain": "example.com"})
            await asyncio.sleep(0)

            mock_deliver.assert_not_awaited()
 
 
@pytest.mark.asyncio
async def test_deliver_skips_already_successful(fake_bus, fake_storage):
    storage_module._instance = FakeStorage()
    storage_module._instance.get_delivery_status = AsyncMock(
        return_value={"success": True,
                      "attempt": 1,
                      "retry_after": None,
                      "first_attempt_at": 1000.0})

    with Cfg({"profed": {"run": "activity_delivery"},
              "api":    {"domain": "example.com"}}):
        with patch("profed.components.activity_delivery.delivery.httpx.AsyncClient"):
            await delivery.deliver({},
                                   "https://example.com/act/1",
                                   ACTIVITY,
                                   "bob@remote.example")

            storage_module._instance.upsert_delivery = AsyncMock()
            storage_module._instance.upsert_delivery.assert_not_awaited()
 
 
@pytest.mark.asyncio
async def test_deliver_publishes_attempt_on_success(fake_bus, fake_storage):
    def _mock_response(status=202):
        r = MagicMock()
        r.status_code = status
        r.headers = {}
        r.raise_for_status = MagicMock()
        r.json.return_value = {"inbox": "https://remote.example/inbox/bob"}
        return r

    with Cfg({"profed": {"run": "activity_delivery"},
              "api":    {"domain": "example.com"}}):
        with patch("profed.components.activity_delivery.delivery.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get  = \
                    AsyncMock(return_value=_mock_response())
            mock_client.return_value.__aenter__.return_value.post = \
                    AsyncMock(return_value=_mock_response())

            await delivery.deliver({"initial_retry": 0},
                                   "https://example.com/act/1",
                                   ACTIVITY,
                                   "bob@remote.example")

            published = fake_bus.topic("deliveries").published
            assert len(published) == 1
            assert published[0]["payload"]["success"] is True
            assert published[0]["payload"]["recipient"] == "bob@remote.example"
 
 
@pytest.mark.asyncio
async def test_deliver_publishes_attempt_on_failure(fake_bus, fake_storage):
    def _mock_response(status):
        r = MagicMock()
        r.status_code = status
        r.headers = {}
        r.raise_for_status = MagicMock()
        r.json.return_value = {"inbox": "https://remote.example/inbox/bob"}
        return r
    with Cfg({"profed": {"run": "activity_delivery"},
              "api":    {"domain": "example.com"}}):
        with patch("profed.components.activity_delivery.delivery.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get  = \
                    AsyncMock(return_value=_mock_response(200))
            mock_client.return_value.__aenter__.return_value.post = \
                    AsyncMock(return_value=_mock_response(500))

            with patch.object(delivery, "deliver", wraps=delivery.deliver) as _:
                await delivery.deliver({"initial_retry": 0},
                                        "https://example.com/act/1",
                                        ACTIVITY, "bob@remote.example")

            published = fake_bus.topic("deliveries").published
            assert len(published) == 1
            assert published[0]["payload"]["success"] is False
            assert published[0]["payload"]["status_code"] == 500

