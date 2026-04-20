# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from profed.core import message_bus
from profed.components.api.c2s.apps.router import router
 
 
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
 
 
@pytest.fixture
def fake_bus():
    backup = message_bus._instance
    message_bus._instance = FakeMessageBus()
    yield message_bus._instance
    message_bus._instance = backup
 
 
@pytest.fixture
def client(fake_bus):
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)
 
 
def test_register_app_returns_credentials(client, fake_bus):
    response = client.post("/api/v1/apps",
                           json={"client_name":   "Tusky",
                                 "redirect_uris": "tusky://callback",
                                 "scopes":        "read write"})
    assert response.status_code == 200
    data = response.json()
    assert "client_id" in data
    assert "client_secret" in data
    assert data["name"] == "Tusky"
    assert data["scopes"] == "read write"
 
 
def test_register_app_publishes_event(client, fake_bus):
    client.post("/api/v1/apps",
                json={"client_name":   "Tusky",
                      "redirect_uris": "tusky://callback",
                      "scopes":        "read write"})
    published = fake_bus.topic("oauth_apps")._ctx.published
    assert len(published) == 1
    assert published[0]["type"] == "created"
    payload = published[0]["payload"]
    assert payload["client_name"] == "Tusky"
    assert payload["redirect_uris"] == "tusky://callback"
 
 
def test_register_app_default_scopes(client, fake_bus):
    response = client.post("/api/v1/apps",
                           json={"client_name":   "MinApp",
                                 "redirect_uris": "myapp://cb"})
    assert response.json()["scopes"] == "read"
 
 
def test_register_app_missing_required_fields_returns_422(client):
    response = client.post("/api/v1/apps", json={"scopes": "read"})
    assert response.status_code == 422
