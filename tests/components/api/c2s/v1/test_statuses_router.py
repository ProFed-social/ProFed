# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import pytest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from profed.core import message_bus
from profed.components.api.c2s.v1.statuses import router as statuses_module
from profed.components.api.c2s.auth import current_user

 
class FakePublishContext:
    def __init__(self): self.published = []
    async def __aenter__(self):
        async def pub(msg, **_): self.published.append(msg)
        return pub
    async def __aexit__(self, *_): pass
 
 
class FakeTopic:
    def __init__(self): self._ctx = FakePublishContext()
    def publish(self): return self._ctx
 
 
class FakeMessageBus:
    def __init__(self): self._topics = {}
    def topic(self, name):
        if name not in self._topics:
            self._topics[name] = FakeTopic()
        return self._topics[name]
 
 
CLAIMS = {"preferred_username": "alice", "sub": "alice"}
 
 
@pytest.fixture
def fake_bus():
    backup = message_bus._instance
    message_bus._instance = FakeMessageBus()
    yield message_bus._instance
    message_bus._instance = backup
 
 
@pytest.fixture
def client(fake_bus):
    statuses_module.init({"status_max_characters": "5000"})
    app = FastAPI()
    app.include_router(statuses_module.router)
    app.dependency_overrides[current_user] = lambda: CLAIMS
    return TestClient(app)
 
 
def test_create_status_publishes_activity(client, fake_bus):
    response = client.post("/statuses",
                           json={"status": "Hello Fediverse!"})

    assert response.status_code == 200
    published = fake_bus.topic("activities")._ctx.published
    assert len(published) == 1
    assert published[0]["type"] == "created"
    assert published[0]["payload"]["type"] == "Create"
    assert published[0]["payload"]["username"] == "alice"
    assert published[0]["payload"]["object"]["type"] == "Note"
    assert published[0]["payload"]["object"]["content"] == "Hello Fediverse!"
 
 
def test_create_status_returns_status_object(client, fake_bus):
    response = client.post("/statuses",
                           json={"status": "Hello Fediverse!"})
    data = response.json()
    assert data["content"] == "Hello Fediverse!"
    assert data["visibility"] == "public"
    assert "id" in data
 
 
def test_create_status_too_long_returns_422(client, fake_bus):
    response = client.post("/statuses",
                           json={"status": "x" * 5001})

    assert response.status_code == 422
 
 
def test_statuses_active_flag_set_after_init():
    statuses_module.init({})
    assert statuses_module.active is True

