# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import os
import pytest
from unittest.mock import AsyncMock, patch
from profed.core import message_bus
from fastapi import FastAPI
from fastapi.testclient import TestClient
from profed.core.config import config, raw
from profed.components.api.c2s.v1.accounts import router as accounts_module
from profed.components.api.c2s.shared.auth import current_user 
 
class Cfg:
    def __init__(self, cfg):
        raw.paths = []
        raw.argv = [""] + [f"--{s}.{k}={v}"
                            for s, d in cfg.items()
                            for k, v in d.items()]
        os.environ = {k: v for k, v in os.environ.items()
                      if not k.startswith("PROFED_")}
 
    def __enter__(self):
        config.reset()
 
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            raise exc_val
 
 
CLAIMS = {"preferred_username": "alice", "sub": "alice"}
 
 
class FakePerson:
    name = "Alice Example"
    summary = "Software engineer"
 
 
@pytest.fixture
def client():
    accounts_module.init({})
    app = FastAPI()
    app.include_router(accounts_module.router)
    app.dependency_overrides[current_user] = lambda: CLAIMS
    return TestClient(app)
 

class FakePublishContext:
    def __init__(self):
        self.published = []

    async def __aenter__(self):
        async def publish(msg): self.published.append(msg)
        return publish

    async def __aexit__(self, *_): pass


class FakeTopic:
    def __init__(self):
        self._ctx = FakePublishContext()

    def publish(self):
        return self._ctx


class FakeMessageBus:
    def __init__(self):
        self._topics = {}

    def topic(self, name):
        if name not in self._topics:
            self._topics[name] = FakeTopic()
        return self._topics[name]
 

def test_verify_credentials_returns_account(client):
    with Cfg({"profed": {"run": "api"},
              "api":    {"domain": "example.com"}}):
        with patch("profed.components.api.c2s.v1.accounts.router.resolve_actor",
                   new=AsyncMock(return_value=FakePerson())):
            response = client.get("/accounts/verify_credentials")

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "alice"
    assert data["display_name"] == "Alice Example"
    assert data["note"] == "Software engineer"
    assert data["acct"] == "alice@example.com"
 
 
def test_verify_credentials_unknown_actor_returns_404(client):
    with Cfg({"profed": {"run": "api"},
              "api":    {"domain": "example.com"}}):
        with patch("profed.components.api.c2s.v1.accounts.router.resolve_actor",
                   new=AsyncMock(return_value=None)):
            response = client.get("/accounts/verify_credentials")
    assert response.status_code == 404
 
 
def test_accounts_active_flag_set_after_init():
    accounts_module.init({})
    assert accounts_module.active is True


ROW = {"account_id": 123456,
       "acct":       "bob@remote.example",
       "actor_url":  "https://remote.example/actors/bob",
       "actor_data": {"type": "Person", "name": "Bob"}}

def test_follow_by_numeric_id_publishes_events(client):
    fake_bus = FakeMessageBus()

    with Cfg({"profed": {"run": "api"},
              "api":    {"domain": "example.com"}}):
        with patch("profed.components.api.c2s.v1.accounts.router._resolve_account",
                   AsyncMock(return_value=ROW)), \
             patch.object(message_bus, "_instance", fake_bus):
            response = client.post("/accounts/123456/follow")

    assert response.status_code == 200
    data = response.json()
    assert data["requested"] is True
    known_accounts_events = fake_bus.topic("known_accounts")._ctx.published
    assert len(known_accounts_events) == 1
    assert known_accounts_events[0]["type"] == "follow_requested"
    assert known_accounts_events[0]["payload"]["account_id"] == 123456
    assert known_accounts_events[0]["payload"]["following_user"] == "alice"
    activities_events = fake_bus.topic("activities")._ctx.published
    assert len(activities_events) == 1
    assert activities_events[0]["payload"]["type"] == "Follow"
    assert activities_events[0]["payload"]["object"] == ROW["actor_url"]


def test_follow_unknown_account_returns_404(client):
    with Cfg({"profed": {"run": "api"},
              "api":    {"domain": "example.com"}}):
        with patch("profed.components.api.c2s.v1.accounts.router._resolve_account",
                   AsyncMock(return_value=None)):
            response = client.post("/accounts/999999/follow")

    assert response.status_code == 404


FOLLOWING_ROW_PENDING  = {"account_id": 42, "following_user": "alice", "accepted": False}
FOLLOWING_ROW_ACCEPTED = {"account_id": 42, "following_user": "alice", "accepted": True}


def _mock_storage(rows):
    mock = AsyncMock()
    mock.get_following = AsyncMock(return_value=rows)
    return AsyncMock(return_value=mock)


def test_relationships_not_following(client):
    with Cfg({"profed": {"run": "api"},
              "api":    {"domain": "example.com"}}):
        with patch("profed.components.api.c2s.v1.accounts.router.following_storage",
                   _mock_storage([])):
            response = client.get("/accounts/relationships?id[]=42")

    assert response.status_code == 200
    data = response.json()
    assert data == [{"id":              "42",
                     "following":       False,
                     "requested":       False,
                     "followed_by":     False,
                     "blocking":        False,
                     "muting":          False,
                     "domain_blocking": False,
                     "endorsed":        False,
                     "note":            ""}]


def test_relationships_follow_requested(client):
    with Cfg({"profed": {"run": "api"},
              "api":    {"domain": "example.com"}}):
        with patch("profed.components.api.c2s.v1.accounts.router.following_storage",
                   _mock_storage([FOLLOWING_ROW_PENDING])):
            response = client.get("/accounts/relationships?id[]=42")

    assert response.status_code == 200
    data = response.json()
    assert data[0]["following"] is False
    assert data[0]["requested"] is True


def test_relationships_following(client):
    with Cfg({"profed": {"run": "api"},
              "api":    {"domain": "example.com"}}):
        with patch("profed.components.api.c2s.v1.accounts.router.following_storage",
                   _mock_storage([FOLLOWING_ROW_ACCEPTED])):
            response = client.get("/accounts/relationships?id[]=42")

    assert response.status_code == 200
    data = response.json()
    assert data[0]["following"] is True
    assert data[0]["requested"] is False

