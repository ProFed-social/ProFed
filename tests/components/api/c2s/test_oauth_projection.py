# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import time
import pytest
from profed.core import message_bus
from profed.components.api.c2s.oauth import projection
 
 
class FakeTopic:
    def __init__(self):
        self.messages = []
        self.published = []
 
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
 
    def publish(self):
        class _Ctx:
            async def __aenter__(self_):
                async def pub(msg, **_): self_.topic.published.append(msg)
                self_.topic = self
                return pub
            async def __aexit__(self_, *_): pass
        return _Ctx()
 
 
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
 
 
APP = {"client_id":     "abc123",
       "client_secret": "secret",
       "client_name":   "TestApp",
       "redirect_uris": "https://app.example.com/callback",
       "scopes":        "read write"}
 
 
@pytest.mark.asyncio
async def test_app_created_added_to_projection(fake_bus):
    fake_bus.topic("oauth_apps").messages = [(1, {"type": "created",
                                                  "payload": APP})]
    await projection.apps_rebuild()
    assert projection.get_app("abc123") == APP
 
 
@pytest.mark.asyncio
async def test_unknown_app_returns_none(fake_bus):
    fake_bus.topic("oauth_apps").messages = []
    await projection.apps_rebuild()
    assert projection.get_app("unknown") is None
 
 
@pytest.mark.asyncio
async def test_code_issued_added_to_projection(fake_bus):
    payload = {"code":       "mycode",
               "client_id":  "abc123",
               "username":   "alice",
               "id_token":   "tok",
               "expires_at": time.time() + 600}
    fake_bus.topic("oauth_codes").messages = [(1, {"type": "issued",
                                                   "payload": payload})]
    await projection.codes_rebuild()
    assert projection.get_code("mycode") == payload
 
 
@pytest.mark.asyncio
async def test_expired_code_returns_none(fake_bus):
    payload = {"code":       "mycode",
               "client_id":  "abc123",
               "username":   "alice",
               "id_token":   "tok",
               "expires_at": time.time() - 1}
    fake_bus.topic("oauth_codes").messages = [(1, {"type": "issued",
                                                   "payload": payload})]
    await projection.codes_rebuild()
    assert projection.get_code("mycode") is None
 
 
@pytest.mark.asyncio
async def test_consumed_code_removed_from_projection(fake_bus):
    payload = {"code":       "mycode",
               "client_id":  "abc123",
               "username":   "alice",
               "id_token":   "tok",
               "expires_at": time.time() + 600}
    fake_bus.topic("oauth_codes").messages = [(1, {"type": "issued",
                                                   "payload": payload}),
                                              (2, {"type": "consumed", 
                                                   "payload": {"code": "mycode"}})]
    await projection.codes_rebuild()
    assert projection.get_code("mycode") is None

