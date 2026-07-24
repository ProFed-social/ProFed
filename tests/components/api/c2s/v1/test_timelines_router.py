# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, patch
from profed.models.mastodon import Account
from fastapi import FastAPI
from fastapi.testclient import TestClient
from profed.components.api.c2s.v1.timelines import router as timelines_module
from profed.components.api.c2s.v1.timelines import storage as timelines_storage
from profed.components.api.c2s.shared.auth import current_user


CLAIMS = {"preferred_username": "alice", "sub": "alice"}

ACTOR_URL = "https://remote.example/actors/bob"
STATUS = {"id": "424242",
          "created_at": "2026-01-01T00:00:00+00:00",
          "uri": "https://example.com/act/1",
          "url": "https://example.com/act/1",
          "content": "Hello!",
          "mentions": [],
          "tags": []}

BOB = Account(id="999",
              username="bob",
              acct="bob@remote.example",
              display_name="Bob",
              url="https://remote.example/actors/bob")


class FakeStorage:
    async def fetch(self, username, limit=20, max_id=None, since_id=None):
        return [(ACTOR_URL, STATUS)]


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
    with patch("profed.components.api.c2s.v1.timelines.router.cached_multiple",
               AsyncMock(return_value={ACTOR_URL: BOB})):
        response = client.get("/timelines/home")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == "424242"
    assert data[0]["content"] == "Hello!"
    assert data[0]["account"]["username"] == "bob"


def test_home_timeline_falls_back_to_a_placeholder_account(client):
    with patch("profed.components.api.c2s.v1.timelines.router.cached_multiple",
               AsyncMock(return_value={})):
        response = client.get("/timelines/home")

    assert response.status_code == 200
    assert response.json()[0]["account"]["username"] == "bob"


def test_home_timeline_does_not_webfinger_on_read(client):
    with patch("profed.components.api.c2s.v1.timelines.router.cached_multiple",
               AsyncMock(return_value={ACTOR_URL: BOB})) as cached:
        client.get("/timelines/home")

    cached.assert_awaited_once()


def test_home_timeline_empty(client):
    timelines_storage._instance.fetch = AsyncMock(return_value=[])

    with patch("profed.components.api.c2s.v1.timelines.router.cached_multiple", AsyncMock(return_value={})):
        response = client.get("/timelines/home")

    assert response.status_code == 200
    assert response.json() == []


def test_timelines_active_flag_set_after_init():
    timelines_module.init({})
    assert timelines_module.active is True


def test_public_timeline_returns_empty_list(client):
    response = client.get("/timelines/public")

    assert response.status_code == 200
    assert response.json() == []


def test_public_timeline_accepts_local_flag(client):
    response = client.get("/timelines/public?local=true")

    assert response.status_code == 200
    assert response.json() == []


def test_hashtag_timeline_returns_empty_list(client):
    response = client.get("/timelines/tag/python")

    assert response.status_code == 200
    assert response.json() == []

