# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import pytest
from unittest.mock import AsyncMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from profed.components.api.c2s.v1.search import router, init
from profed.components.api.c2s.v1.search.resolvers.accounts import _actor_to_account
from profed.components.api.c2s.shared.auth import current_user 
 
@pytest.fixture
def client():
    app = FastAPI()
    init({})
    app.include_router(router, prefix="")
    app.dependency_overrides[current_user] = lambda: {"sub": "christof"}
    yield TestClient(app) 
 
ACTOR = {"id":   "https://mastodon.social/users/alice",
         "type": "Person",
         "name": "Alice"}
ROW = {"account_id":        123456,
       "acct":              "alice@mastodon.social",
       "actor_url":         "https://mastodon.social/users/alice",
       "actor_data":        ACTOR,
       "last_webfinger_at": "2026-04-28T12:00:00+00:00"} 

 
def test_search_without_resolve_returns_empty(client):
    response = client.get("/search?q=@alice@mastodon.social")

    assert response.status_code == 200
    assert response.json() == {}
 
 
def test_search_non_acct_returns_empty(client):
    response = client.get("/search?q=python&resolve=true")

    assert response.status_code == 200
    assert response.json() == {}
 
 
def test_search_with_resolve_returns_account(client):
    with patch("profed.components.api.c2s.v1.search.resolvers.accounts.lookup_by_acct",
               AsyncMock(return_value=ROW)):
        response = client.get("/search?q=@alice@mastodon.social&resolve=true")

    assert response.status_code == 200
    result = response.json()
    assert "accounts" in result
    assert len(result["accounts"]) == 1
    assert result["accounts"][0]["acct"] == "alice@mastodon.social"
 
 
def test_search_type_filter_limits_resolvers(client):
    with patch("profed.components.api.c2s.v1.search.resolvers.accounts.lookup_by_acct",
               AsyncMock(return_value=None)):
        response = client.get("/search?q=@alice@mastodon.social&resolve=true&type=statuses")

    assert response.status_code == 200
    assert response.json() == {}
 
 
def test_actor_to_account_maps_fields():
    acct   = "alice@mastodon.social"
    result = _actor_to_account(ACTOR, acct)

    assert result["username"]     == "alice"
    assert result["acct"]         == acct
    assert result["display_name"] == "Alice"
    assert result["url"]          == ACTOR["id"]

