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


def test_follow_publishes_follow_activity_id_in_known_accounts_event(client):
    fake_bus = FakeMessageBus()

    with Cfg({"profed": {"run": "api"},
              "api":    {"domain": "example.com"}}):
        with patch("profed.components.api.c2s.v1.accounts.router._resolve_account",
                   AsyncMock(return_value=ROW)), \
             patch.object(message_bus, "_instance", fake_bus):
            response = client.post("/accounts/123456/follow")

    assert response.status_code == 200
    known_accounts_events = fake_bus.topic("known_accounts")._ctx.published
    payload = known_accounts_events[0]["payload"]
    assert "follow_activity_id" in payload
    follow_id = payload["follow_activity_id"]
    assert follow_id.startswith("https://example.com/actors/alice#follows/")
    activities_events = fake_bus.topic("activities")._ctx.published
    assert activities_events[0]["payload"]["id"] == follow_id


FOLLOWING_WITH_ACTIVITY_ID = {"account_id":         123456,
                               "following_user":     "alice",
                               "accepted":           False,
                               "follow_activity_id": "https://example.com/actors/alice#follows/test-uuid"}


def _mock_storage_with(row):
    mock = AsyncMock()
    mock.get_following = AsyncMock(return_value=[row] if row else [])
    mock.get           = AsyncMock(return_value=row)
    return AsyncMock(return_value=mock)


def test_unfollow_publishes_known_accounts_event(client):
    fake_bus = FakeMessageBus()

    with Cfg({"profed": {"run": "api"},
              "api":    {"domain": "example.com"}}):
        with patch("profed.components.api.c2s.v1.accounts.router._resolve_account",
                   AsyncMock(return_value=ROW)), \
             patch("profed.components.api.c2s.v1.accounts.router.following_storage",
                   _mock_storage_with(FOLLOWING_WITH_ACTIVITY_ID)), \
             patch.object(message_bus, "_instance", fake_bus):
            response = client.post("/accounts/123456/unfollow")

    assert response.status_code == 200
    assert response.json() == {"id": "123456", "following": False, "requested": False}
    events = fake_bus.topic("known_accounts")._ctx.published
    assert len(events) == 1
    assert events[0]["type"] == "unfollow"
    assert events[0]["payload"]["account_id"]    == 123456
    assert events[0]["payload"]["following_user"] == "alice"


def test_unfollow_publishes_undo_follow_with_correct_follow_id(client):
    fake_bus = FakeMessageBus()

    with Cfg({"profed": {"run": "api"},
              "api":    {"domain": "example.com"}}):
        with patch("profed.components.api.c2s.v1.accounts.router._resolve_account",
                   AsyncMock(return_value=ROW)), \
             patch("profed.components.api.c2s.v1.accounts.router.following_storage",
                   _mock_storage_with(FOLLOWING_WITH_ACTIVITY_ID)), \
             patch.object(message_bus, "_instance", fake_bus):
            response = client.post("/accounts/123456/unfollow")

    assert response.status_code == 200
    events = fake_bus.topic("activities")._ctx.published
    assert len(events) == 1
    payload = events[0]["payload"]
    assert payload["type"]  == "Undo"
    assert payload["actor"] == "https://example.com/actors/alice"
    obj = payload["object"]
    assert obj["type"]   == "Follow"
    assert obj["id"]     == FOLLOWING_WITH_ACTIVITY_ID["follow_activity_id"]
    assert obj["actor"]  == "https://example.com/actors/alice"
    assert obj["object"] == ROW["actor_url"]


def test_unfollow_without_follow_activity_id_uses_fallback_id(client):
    fake_bus = FakeMessageBus()
    following_no_id = {**FOLLOWING_WITH_ACTIVITY_ID, "follow_activity_id": None}

    with Cfg({"profed": {"run": "api"},
              "api":    {"domain": "example.com"}}):
        with patch("profed.components.api.c2s.v1.accounts.router._resolve_account",
                   AsyncMock(return_value=ROW)), \
             patch("profed.components.api.c2s.v1.accounts.router.following_storage",
                   _mock_storage_with(following_no_id)), \
             patch.object(message_bus, "_instance", fake_bus):
            response = client.post("/accounts/123456/unfollow")

    assert response.status_code == 200
    events = fake_bus.topic("activities")._ctx.published
    assert len(events) == 1
    assert events[0]["payload"]["object"]["id"].endswith("#follows/123456")


def test_unfollow_unknown_account_returns_404(client):
    with Cfg({"profed": {"run": "api"},
              "api":    {"domain": "example.com"}}):
        with patch("profed.components.api.c2s.v1.accounts.router._resolve_account",
                   AsyncMock(return_value=None)):
            response = client.post("/accounts/999999/unfollow")

    assert response.status_code == 404


ROW_FULL = {"account_id": 123456,
            "acct": "bob@remote.example",
            "actor_url": "https://remote.example/actors/bob",
            "actor_data": {"type": "Person",
                           "name": "Bob Example",
                           "summary": "A test user",
                           "icon": {"url": "https://remote.example/avatar.png"},
                           "image": {"url": "https://remote.example/header.png"},
                           "manuallyApprovesFollowers": False}}


ROW_FOLLOWING = {"account_id": 789,
                 "acct": "alice@other.example",
                 "actor_url": "https://other.example/actors/alice",
                 "actor_data": {"type": "Person", "name": "Alice"}}


def test_account_from_known_account_returns_correct_fields():
    from profed.components.api.c2s.v1.accounts.router import _account_from_known_account

    result = _account_from_known_account(ROW_FULL)

    assert result.id == "123456"
    assert result.username == "bob"
    assert result.acct == "bob@remote.example"
    assert result.display_name == "Bob Example"
    assert result.note == "A test user"
    assert result.url == "https://remote.example/actors/bob"
    assert result.avatar == "https://remote.example/avatar.png"
    assert result.header == "https://remote.example/header.png"
    assert result.locked is False
    assert result.bot is False


def test_account_from_known_account_falls_back_to_username_for_display_name():
    from profed.components.api.c2s.v1.accounts.router import _account_from_known_account

    row    = {**ROW, "actor_data": {"type": "Person"}}

    result = _account_from_known_account(row)

    assert result.display_name == "bob"


def test_lookup_returns_account(client):
    with patch("profed.components.api.c2s.v1.accounts.router._resolve_account",
               AsyncMock(return_value=ROW_FULL)):
        response = client.get("/accounts/lookup?acct=bob@remote.example")

    assert response.status_code == 200
    data = response.json()
    assert data["id"]       == "123456"
    assert data["username"] == "bob"
    assert data["acct"]     == "bob@remote.example"


def test_lookup_returns_404_when_not_found(client):
    with patch("profed.components.api.c2s.v1.accounts.router._resolve_account",
               AsyncMock(return_value=None)):
        response = client.get("/accounts/lookup?acct=nobody@example.com")

    assert response.status_code == 404


def test_get_account_returns_account(client):
    with patch("profed.components.api.c2s.v1.accounts.router._resolve_account",
               AsyncMock(return_value=ROW_FULL)):
        response = client.get("/accounts/123456")

    assert response.status_code == 200
    assert response.json()["id"] == "123456"


def test_get_account_returns_404_when_not_found(client):
    with patch("profed.components.api.c2s.v1.accounts.router._resolve_account",
               AsyncMock(return_value=None)):
        response = client.get("/accounts/999999")

    assert response.status_code == 404


def test_account_followers_returns_accounts(client):
    mock_followers = AsyncMock()
    mock_followers.get_followers = AsyncMock(return_value=["alice@other.example"])

    with patch("profed.components.api.c2s.v1.accounts.router._resolve_account",
               AsyncMock(return_value=ROW_FULL)), \
         patch("profed.components.api.c2s.v1.accounts.router.c2s_followers_storage",
               AsyncMock(return_value=mock_followers)), \
         patch("profed.components.api.c2s.v1.accounts.router.lookup_by_acct",
               AsyncMock(return_value=ROW_FOLLOWING)):
        response = client.get("/accounts/123456/followers")

    assert response.status_code == 200
    data = response.json()
    assert len(data)           == 1
    assert data[0]["username"] == "alice"


def test_account_followers_skips_unknown_followers(client):
    mock_followers = AsyncMock()
    mock_followers.get_followers = AsyncMock(return_value=["unknown@gone.example"])

    with patch("profed.components.api.c2s.v1.accounts.router._resolve_account",
               AsyncMock(return_value=ROW_FULL)), \
         patch("profed.components.api.c2s.v1.accounts.router.c2s_followers_storage",
               AsyncMock(return_value=mock_followers)), \
         patch("profed.components.api.c2s.v1.accounts.router.lookup_by_acct",
               AsyncMock(return_value=None)):
        response = client.get("/accounts/123456/followers")

    assert response.status_code == 200
    assert response.json() == []


def test_account_followers_returns_404_when_account_not_found(client):
    with patch("profed.components.api.c2s.v1.accounts.router._resolve_account",
               AsyncMock(return_value=None)):
        response = client.get("/accounts/999999/followers")

    assert response.status_code == 404


def test_account_following_returns_accounts_for_known_user(client):
    mock_storage = AsyncMock()
    mock_storage.get_following = AsyncMock(
        return_value=[{"account_id":        789,
                       "accepted":           True,
                       "follow_activity_id": None}])

    with patch("profed.components.api.c2s.v1.accounts.router._resolve_account",
               AsyncMock(return_value=ROW_FULL)), \
         patch("profed.components.api.c2s.v1.accounts.router.following_storage",
               AsyncMock(return_value=mock_storage)), \
         patch("profed.components.api.c2s.v1.accounts.router.lookup_by_id",
               AsyncMock(return_value=ROW_FOLLOWING)):
        response = client.get("/accounts/123456/following")

    assert response.status_code == 200
    data = response.json()
    assert len(data)           == 1
    assert data[0]["id"]       == "789"
    assert data[0]["username"] == "alice"


def test_account_following_skips_unresolvable_accounts(client):
    mock_storage = AsyncMock()
    mock_storage.get_following = AsyncMock(
        return_value=[{"account_id":        789,
                       "accepted":           True,
                       "follow_activity_id": None}])

    with patch("profed.components.api.c2s.v1.accounts.router._resolve_account",
               AsyncMock(return_value=ROW_FULL)), \
         patch("profed.components.api.c2s.v1.accounts.router.following_storage",
               AsyncMock(return_value=mock_storage)), \
         patch("profed.components.api.c2s.v1.accounts.router.lookup_by_id",
               AsyncMock(return_value=None)):
        response = client.get("/accounts/123456/following")

    assert response.status_code == 200
    assert response.json() == []


def test_account_following_returns_404_when_account_not_found(client):
    with patch("profed.components.api.c2s.v1.accounts.router._resolve_account",
               AsyncMock(return_value=None)):
        response = client.get("/accounts/999999/following")

    assert response.status_code == 404

