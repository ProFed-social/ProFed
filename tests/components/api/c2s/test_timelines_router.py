# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import pytest
from unittest.mock import AsyncMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from profed.components.api.c2s.timelines import router as timelines_module
from profed.components.api.c2s.timelines import storage as timelines_storage
from profed.components.api.c2s.auth import current_user

 
CLAIMS = {"preferred_username": "alice", "sub": "alice"}
 
ACTIVITY = {"id":     "https://example.com/act/1",
            "type":   "Create",
            "actor":  "https://remote.example/actors/bob",
            "object": {"type":      "Note",
                       "content":   "Hello!",
                       "published": "2026-01-01T00:00:00+00:00"}}
 
 
class FakeStorage:
    async def fetch(self, username, limit=20, max_id=None, since_id=None):
        return [("uuid-1", ACTIVITY)]
 
 
@pytest.fixture
def client():
    timelines_module.init({})
    timelines_storage._instance = FakeStorage()
    app = FastAPI()
    app.include_router(timelines_module.router)
    app.dependency_overrides[current_user] = lambda: CLAIMS
    yield TestClient(app)
    timelines_storage._instance = None
 
 
def test_home_timeline_returns_statuses(client):
    response = client.get("/timelines/home")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "uuid-1"
    assert data[0]["content"] == "Hello!"
    assert data[0]["account"]["username"] == "bob"
 
 
def test_home_timeline_empty(client):
    timelines_storage._instance.fetch = AsyncMock(return_value=[])
    response = client.get("/timelines/home")

    assert response.status_code == 200
    assert response.json() == []
 
 
def test_timelines_active_flag_set_after_init():
    timelines_module.init({})
    assert timelines_module.active is True

