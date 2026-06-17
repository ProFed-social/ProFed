# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import os
import pytest
from unittest.mock import AsyncMock, patch
from profed.core import message_bus
from fastapi import FastAPI
from fastapi.testclient import TestClient
from profed.core.config import config, raw
from profed.identity import account_id
from profed.models.mastodon import Account
from profed.components.api.c2s.shared.known_accounts.service import make_account
from profed.components.api.c2s.v1.accounts import router as accounts_module
from profed.components.api.c2s.shared.auth import current_user 
from profed.core.message_bus.source_key import source_key
 
from _fakes import FakeMessageBus


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
 
 
LOCAL_ACCOUNT = Account(id="1",
                        username="alice",
                        acct="alice@example.com",
                        display_name="Alice Example",
                        note="Software engineer",
                        url="https://example.com/actors/alice")
 
 
@pytest.fixture
def client():
    accounts_module.init({})
    app = FastAPI()
    app.include_router(accounts_module.router)
    app.dependency_overrides[current_user] = lambda: CLAIMS
    return TestClient(app)


@pytest.fixture
def anon_client():
    accounts_module.init({})
    app = FastAPI()
    app.include_router(accounts_module.router)
    return TestClient(app) 


def test_verify_credentials_returns_account(client):
    with Cfg({"profed": {"run": "api"},
              "api":    {"domain": "example.com"}}):
        with patch("profed.components.api.c2s.v1.accounts.router.resolve_actor",
                   new=AsyncMock(return_value=LOCAL_ACCOUNT)):
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
                   AsyncMock(return_value=make_account(ROW))), \
             patch.object(message_bus, "_instance", fake_bus):
            response = client.post("/accounts/123456/follow")

    assert response.status_code == 200
    data = response.json()
    assert data["requested"] is True
    activities_events = fake_bus.topic("activities").published
    assert len(activities_events) == 1
    assert activities_events[0]["event_type"] == "Follow"
    assert activities_events[0]["payload"]["activity"]["object"] == ROW["actor_url"]


def test_follow_publishes_followers_requested(client):
    fake_bus = FakeMessageBus()

    with Cfg({"profed": {"run": "api"},
              "api":    {"domain": "example.com"}}):
        with patch("profed.components.api.c2s.v1.accounts.router._resolve_account",
                   AsyncMock(return_value=make_account(ROW))), \
             patch.object(message_bus, "_instance", fake_bus):
            client.post("/accounts/123456/follow")

    events = fake_bus.topic("followers").published
    assert len(events) == 1
    assert events[0]["event_type"] == "requested"
    assert events[0]["object_id"] == "alice@example.com|bob@remote.example"
    assert "follow_activity_id" in events[0]["payload"]


def test_follow_unknown_account_returns_404(client):
    with Cfg({"profed": {"run": "api"},
              "api":    {"domain": "example.com"}}):
        with patch("profed.components.api.c2s.v1.accounts.router._resolve_account",
                   AsyncMock(return_value=None)):
            response = client.post("/accounts/999999/follow")

    assert response.status_code == 404


FLAGS_NONE = {42: {"following": False, "requested": False, "followed_by": False}}
FLAGS_REQUESTED = {42: {"following": False, "requested": True, "followed_by": False}}
FLAGS_FOLLOWING = {42: {"following": True, "requested": False, "followed_by": False}}
FLAGS_FOLLOWED_BY = {42: {"following": False, "requested": False, "followed_by": True}}


def _relationships_storage(flags):
    mock = AsyncMock()
    mock.relationships = AsyncMock(return_value=flags)
    return AsyncMock(return_value=mock)


def test_relationships_not_following(client):
    with Cfg({"profed": {"run": "api"},
              "api":    {"domain": "example.com"}}):
        with patch("profed.components.api.c2s.v1.accounts.router.follows_storage",
                   _relationships_storage(FLAGS_NONE)):
            response = client.get("/accounts/relationships?id[]=42")

    assert response.status_code == 200
    data = response.json()
    assert data == [{"id": "42",
                     "following": False,
                     "requested": False,
                     "followed_by": False,
                     "blocking": False,
                     "muting": False,
                     "domain_blocking": False,
                     "endorsed": False,
                     "note": ""}]


def test_relationships_follow_requested(client):
    with Cfg({"profed": {"run": "api"},
              "api": {"domain": "example.com"}}):
        with patch("profed.components.api.c2s.v1.accounts.router.follows_storage",
                   _relationships_storage(FLAGS_REQUESTED)):
            response = client.get("/accounts/relationships?id[]=42")

    assert response.status_code == 200
    data = response.json()
    assert data[0]["following"] is False
    assert data[0]["requested"] is True


def test_relationships_following(client):
    with Cfg({"profed": {"run": "api"},
              "api": {"domain": "example.com"}}):
        with patch("profed.components.api.c2s.v1.accounts.router.follows_storage",
                   _relationships_storage(FLAGS_FOLLOWING)):
            response = client.get("/accounts/relationships?id[]=42")

    assert response.status_code == 200
    data = response.json()
    assert data[0]["following"] is True
    assert data[0]["requested"] is False


def test_relationships_followed_by(client):
    with Cfg({"profed": {"run": "api"},
              "api": {"domain": "example.com"}}):
        with patch("profed.components.api.c2s.v1.accounts.router.follows_storage",
                   _relationships_storage(FLAGS_FOLLOWED_BY)):
            response = client.get("/accounts/relationships?id[]=42")

    assert response.status_code == 200
    data = response.json()
    assert data[0]["followed_by"] is True
    assert data[0]["following"] is False


def test_follow_requests_returns_pending_accounts(client):
    follows = AsyncMock()
    follows.follow_requests = AsyncMock(return_value=[{"follower": "bob@remote.example",
                                                       "follower_id": 123456,
                                                       "follow_activity_id": None}])

    with Cfg({"profed": {"run": "api"},
              "api": {"domain": "example.com"}}):
        with patch("profed.components.api.c2s.v1.accounts.router.follows_storage",
                   AsyncMock(return_value=follows)), \
             patch("profed.components.api.c2s.v1.accounts.router.lookup_by_acct",
                   AsyncMock(return_value=ROW)):
            response = client.get("/follow_requests")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == account_id(ROW["acct"])


def test_authorize_publishes_accepted_and_federates(client):
    fake_bus = FakeMessageBus()
    follows = AsyncMock()
    follows.get = AsyncMock(return_value={"follow_activity_id": "https://remote.example/follows/1"})

    with Cfg({"profed": {"run": "api"},
              "api": {"domain": "example.com"}}):
        with patch("profed.components.api.c2s.v1.accounts.router.lookup_by_id",
                   AsyncMock(return_value=ROW)), \
             patch("profed.components.api.c2s.v1.accounts.router.follows_storage",
                   AsyncMock(return_value=follows)), \
             patch.object(message_bus, "_instance", fake_bus):
            response = client.post("/follow_requests/123456/authorize")

    assert response.status_code == 200
    assert response.json()["followed_by"] is True
    followers = fake_bus.topic("followers").published
    assert followers[0]["event_type"] == "accepted"
    assert followers[0]["object_id"] == "bob@remote.example|alice@example.com"
    assert fake_bus.topic("activities").published[0]["event_type"] == "Accept"


def test_reject_publishes_rejected_and_federates(client):
    fake_bus = FakeMessageBus()
    follows = AsyncMock()
    follows.get = AsyncMock(return_value={"follow_activity_id": "https://remote.example/follows/1"})

    with Cfg({"profed": {"run": "api"},
              "api": {"domain": "example.com"}}):
        with patch("profed.components.api.c2s.v1.accounts.router.lookup_by_id",
                   AsyncMock(return_value=ROW)), \
             patch("profed.components.api.c2s.v1.accounts.router.follows_storage",
                   AsyncMock(return_value=follows)), \
             patch.object(message_bus, "_instance", fake_bus):
            response = client.post("/follow_requests/123456/reject")

    assert response.status_code == 200
    assert response.json()["followed_by"] is False
    assert fake_bus.topic("followers").published[0]["event_type"] == "rejected"
    assert fake_bus.topic("activities").published[0]["event_type"] == "Reject"


def test_follow_publishes_follow_activity_id_consistently(client):
    fake_bus = FakeMessageBus()

    with Cfg({"profed": {"run": "api"},
              "api":    {"domain": "example.com"}}):
        with patch("profed.components.api.c2s.v1.accounts.router._resolve_account",
                   AsyncMock(return_value=make_account(ROW))), \
             patch.object(message_bus, "_instance", fake_bus):
            response = client.post("/accounts/123456/follow")

    assert response.status_code == 200
    follow_id = fake_bus.topic("followers").published[0]["payload"]["follow_activity_id"]
    assert follow_id.startswith("https://example.com/actors/alice#follows/")
    activities_events = fake_bus.topic("activities").published
    assert activities_events[0]["object_id"] == follow_id


FOLLOWING_WITH_ACTIVITY_ID = {"account_id":         123456,
                               "following_user":     "alice",
                               "accepted":           False,
                               "follow_activity_id": "https://example.com/actors/alice#follows/test-uuid"}


def _mock_storage_with(row):
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=row)
    return AsyncMock(return_value=mock)


def test_unfollow_returns_relationship(client):
    fake_bus = FakeMessageBus()

    with Cfg({"profed": {"run": "api"},
              "api":    {"domain": "example.com"}}):
        with patch("profed.components.api.c2s.v1.accounts.router._resolve_account",
                   AsyncMock(return_value=make_account(ROW))), \
             patch("profed.components.api.c2s.v1.accounts.router.follows_storage",
                   _mock_storage_with(FOLLOWING_WITH_ACTIVITY_ID)), \
             patch.object(message_bus, "_instance", fake_bus):
            response = client.post("/accounts/123456/unfollow")

    assert response.status_code == 200
    assert response.json() == {"id": account_id(ROW["acct"]), "following": False, "requested": False}
    assert fake_bus.topic("known_accounts").published == []


def test_unfollow_publishes_followers_deleted(client):
    fake_bus = FakeMessageBus()

    with Cfg({"profed": {"run": "api"},
              "api":    {"domain": "example.com"}}):
        with patch("profed.components.api.c2s.v1.accounts.router._resolve_account",
                   AsyncMock(return_value=make_account(ROW))), \
             patch("profed.components.api.c2s.v1.accounts.router.follows_storage",
                   _mock_storage_with(FOLLOWING_WITH_ACTIVITY_ID)), \
             patch.object(message_bus, "_instance", fake_bus):
            client.post("/accounts/123456/unfollow")

    events = fake_bus.topic("followers").published
    assert len(events) == 1
    assert events[0]["event_type"] == "deleted"
    assert events[0]["object_id"] == "alice@example.com|bob@remote.example"

def test_unfollow_publishes_undo_follow_with_correct_follow_id(client):
    fake_bus = FakeMessageBus()

    with Cfg({"profed": {"run": "api"},
              "api":    {"domain": "example.com"}}):
        with patch("profed.components.api.c2s.v1.accounts.router._resolve_account",
                   AsyncMock(return_value=make_account(ROW))), \
             patch("profed.components.api.c2s.v1.accounts.router.follows_storage",
                   _mock_storage_with(FOLLOWING_WITH_ACTIVITY_ID)), \
             patch.object(message_bus, "_instance", fake_bus):
            response = client.post("/accounts/123456/unfollow")

    assert response.status_code == 200
    events = fake_bus.topic("activities").published
    assert len(events) == 1
    assert events[0]["event_type"] == "Undo"
    activity = events[0]["payload"]["activity"]
    assert activity["actor"]      == "https://example.com/actors/alice"
    obj = activity["object"]
    assert obj["type"] == "Follow"
    assert obj["id"] == FOLLOWING_WITH_ACTIVITY_ID["follow_activity_id"]
    assert obj["actor"] == "https://example.com/actors/alice"
    assert obj["object"] == ROW["actor_url"]


def test_unfollow_without_follow_activity_id_uses_fallback_id(client):
    fake_bus = FakeMessageBus()
    following_no_id = {**FOLLOWING_WITH_ACTIVITY_ID, "follow_activity_id": None}

    with Cfg({"profed": {"run": "api"},
              "api":    {"domain": "example.com"}}):
        with patch("profed.components.api.c2s.v1.accounts.router._resolve_account",
                   AsyncMock(return_value=make_account(ROW))), \
             patch("profed.components.api.c2s.v1.accounts.router.follows_storage",
                   _mock_storage_with(following_no_id)), \
             patch.object(message_bus, "_instance", fake_bus):
            response = client.post("/accounts/123456/unfollow")

    assert response.status_code == 200
    events = fake_bus.topic("activities").published
    assert len(events) == 1
    assert events[0]["payload"]["activity"]["object"]["id"].endswith(f"#follows/{account_id(ROW['acct'])}")


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


def test_lookup_returns_account(client):
    with patch("profed.components.api.c2s.v1.accounts.router._resolve_account",
               AsyncMock(return_value=make_account(ROW_FULL))):
        response = client.get("/accounts/lookup?acct=bob@remote.example")

    assert response.status_code == 200
    data = response.json()
    assert data["id"]       == account_id(ROW_FULL["acct"])
    assert data["username"] == "bob"
    assert data["acct"]     == "bob@remote.example"


LOCAL_ROW = {"account_id": 7,
             "acct":       "alice@example.com",
             "actor_url":  "https://example.com/actors/alice",
             "actor_data": {"type": "Person", "name": "Alice"}}


def _count_storage(n):
    mock = AsyncMock()
    mock.count = AsyncMock(return_value=n)
    mock.count_followers = AsyncMock(return_value=n)
    mock.count_following = AsyncMock(return_value=n)
    return AsyncMock(return_value=mock)


def _follows_count_storage(followers, following):
    mock = AsyncMock()
    mock.count_followers = AsyncMock(return_value=followers)
    mock.count_following = AsyncMock(return_value=following)
    return AsyncMock(return_value=mock)


def test_lookup_local_account_includes_counts(client):
    with Cfg({"profed": {"run": "api"},
              "api":    {"domain": "example.com"}}):
        with patch("profed.components.api.c2s.v1.accounts.router._resolve_account",
                   AsyncMock(return_value=make_account(LOCAL_ROW))), \
             patch("profed.components.api.c2s.v1.accounts.router.user_statuses_storage",
                   _count_storage(3)), \
             patch("profed.components.api.c2s.v1.accounts.router.follows_storage",
                   _follows_count_storage(5, 2)):
            response = client.get("/accounts/lookup?acct=alice@example.com")

    assert response.status_code == 200
    data = response.json()
    assert data["statuses_count"] == 3
    assert data["followers_count"] == 5
    assert data["following_count"] == 2


def test_lookup_remote_account_keeps_zero_counts(client):
    with Cfg({"profed": {"run": "api"},
              "api":    {"domain": "example.com"}}):
        with patch("profed.components.api.c2s.v1.accounts.router._resolve_account",
                   AsyncMock(return_value=make_account(ROW_FULL))):
            response = client.get("/accounts/lookup?acct=bob@remote.example")

    assert response.status_code == 200
    data = response.json()
    assert data["statuses_count"] == 0
    assert data["followers_count"] == 0
    assert data["following_count"] == 0


def test_lookup_returns_404_when_not_found(client):
    with patch("profed.components.api.c2s.v1.accounts.router._resolve_account",
               AsyncMock(return_value=None)):
        response = client.get("/accounts/lookup?acct=nobody@example.com")

    assert response.status_code == 404


def test_get_account_returns_account(client):
    with patch("profed.components.api.c2s.v1.accounts.router._resolve_account",
               AsyncMock(return_value=make_account(ROW_FULL))):
        response = client.get("/accounts/123456")

    assert response.status_code == 200
    assert response.json()["id"] == account_id(ROW_FULL["acct"])


def test_get_account_returns_404_when_not_found(client):
    with patch("profed.components.api.c2s.v1.accounts.router._resolve_account",
               AsyncMock(return_value=None)):
        response = client.get("/accounts/999999")

    assert response.status_code == 404


def test_account_followers_returns_accounts(client):
    mock_followers = AsyncMock()
    mock_followers.get_followers = AsyncMock(return_value=["alice@other.example"])

    resolved = {"123456": make_account(ROW_FULL),
                "alice@other.example": make_account(ROW_FOLLOWING)}
    with patch("profed.components.api.c2s.v1.accounts.router._resolve_account",
               AsyncMock(side_effect=lambda query, _config: resolved.get(query))), \
         patch("profed.components.api.c2s.v1.accounts.router.follows_storage",
               AsyncMock(return_value=mock_followers)):
        response = client.get("/accounts/123456/followers")

    assert response.status_code == 200
    data = response.json()
    assert len(data)           == 1
    assert data[0]["username"] == "alice"


def test_account_followers_skips_unknown_followers(client):
    mock_followers = AsyncMock()
    mock_followers.get_followers = AsyncMock(return_value=["unknown@gone.example"])

    resolved = {"123456": make_account(ROW_FULL)}
    with patch("profed.components.api.c2s.v1.accounts.router._resolve_account",
               AsyncMock(side_effect=lambda query, _config: resolved.get(query))), \
         patch("profed.components.api.c2s.v1.accounts.router.follows_storage",
               AsyncMock(return_value=mock_followers)):
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
    mock_storage.get_following = AsyncMock(return_value=["alice@other.example"])

    resolved = {"123456": make_account(ROW_FULL),
                "alice@other.example": make_account(ROW_FOLLOWING)}
    with patch("profed.components.api.c2s.v1.accounts.router._resolve_account",
               AsyncMock(side_effect=lambda query, _config: resolved.get(query))), \
         patch("profed.components.api.c2s.v1.accounts.router.follows_storage",
               AsyncMock(return_value=mock_storage)):
        response = client.get("/accounts/123456/following")

    assert response.status_code == 200
    data = response.json()
    assert len(data)           == 1
    assert data[0]["id"]       == account_id(ROW_FOLLOWING["acct"])
    assert data[0]["username"] == "alice"


def test_account_following_skips_unresolvable_accounts(client):
    mock_storage = AsyncMock()
    mock_storage.get_following = AsyncMock(return_value=["alice@other.example"])

    resolved = {"123456": make_account(ROW_FULL)}
    with patch("profed.components.api.c2s.v1.accounts.router._resolve_account",
               AsyncMock(side_effect=lambda query, _config: resolved.get(query))), \
         patch("profed.components.api.c2s.v1.accounts.router.follows_storage",
               AsyncMock(return_value=mock_storage)):
        response = client.get("/accounts/123456/following")

    assert response.status_code == 200
    assert response.json() == []


def test_account_following_returns_404_when_account_not_found(client):
    with patch("profed.components.api.c2s.v1.accounts.router._resolve_account",
               AsyncMock(return_value=None)):
        response = client.get("/accounts/999999/following")

    assert response.status_code == 404


def test_block_account_returns_relationship_with_blocking_true(client):
    response = client.post("/accounts/123/block")

    assert response.status_code == 200
    assert response.json()["blocking"] is True


def test_unblock_account_returns_relationship_with_blocking_false(client):
    response = client.post("/accounts/123/unblock")

    assert response.status_code == 200
    assert response.json()["blocking"] is False


def test_mute_account_returns_relationship_with_muting_true(client):
    response = client.post("/accounts/123/mute")

    assert response.status_code == 200
    assert response.json()["muting"] is True


def test_unmute_account_returns_relationship_with_muting_false(client):
    response = client.post("/accounts/123/unmute")

    assert response.status_code == 200
    assert response.json()["muting"] is False


def test_get_blocks_returns_empty_list(client):
    assert client.get("/blocks").json() == []


def test_get_mutes_returns_empty_list(client):
    assert client.get("/mutes").json() == []


def test_get_preferences_returns_defaults(client):
    response = client.get("/preferences")
    assert response.status_code == 200
    assert response.json()["posting:default:visibility"] == "public"


def test_update_credentials_returns_account(client):
    with patch("profed.components.api.c2s.v1.accounts.router.resolve_actor",
               AsyncMock(return_value=LOCAL_ACCOUNT)):
        response = client.patch("/accounts/update_credentials")

    assert response.status_code == 200
    assert response.json()["username"] == "alice"


def test_get_featured_tags_returns_empty_list(client):
    assert client.get("/featured_tags").json() == []


def test_get_followed_tags_returns_empty_list(client):
    assert client.get("/followed_tags").json() == []


def test_get_suggestions_returns_empty_list(client):
    assert client.get("/suggestions").json() == []


def test_account_statuses_anonymous_returns_list(anon_client):
    storage_mock = AsyncMock(fetch=AsyncMock(return_value=[]))
    with Cfg({"profed": {"run": "api"},
              "api":    {"domain": "example.com"}}):
        with patch("profed.components.api.c2s.v1.accounts.router._resolve_account",
                   AsyncMock(return_value=make_account(ROW_FULL))), \
             patch("profed.components.api.c2s.v1.accounts.router.user_statuses_storage",
                   AsyncMock(return_value=storage_mock)):

            response = anon_client.get("/accounts/123456/statuses")

    assert response.status_code == 200
    assert response.json() == []


def test_account_statuses_returns_rendered_statuses(anon_client):
    activity = {"id": "https://example.com/actors/bob#create/1",
                "actor": "https://example.com/actors/bob",
                "object": {"id": "https://example.com/actors/bob/notes/1",
                           "content": "<p>hello world</p>",
                           "published": "2026-01-01T00:00:00.000Z"}}
    storage_mock = AsyncMock(fetch=AsyncMock(return_value=[(42, activity)]))
    with Cfg({"profed": {"run": "api"}, "api": {"domain": "example.com"}}):
        with patch("profed.components.api.c2s.v1.accounts.router._resolve_account",
                   AsyncMock(return_value=make_account(ROW_FULL))), \
             patch("profed.components.api.c2s.v1.accounts.router.user_statuses_storage",
                   AsyncMock(return_value=storage_mock)):

            response = anon_client.get("/accounts/123456/statuses")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["content"] == "<p>hello world</p>"
    assert data[0]["id"] == str(source_key("activities").message_id(42))

