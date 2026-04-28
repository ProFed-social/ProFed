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
 
 
def test_search_without_resolve_returns_empty(client):
    response = client.get("/search?q=@alice@mastodon.social")

    assert response.status_code == 200
    assert response.json() == {}
 
 
def test_search_non_acct_returns_empty(client):
    response = client.get("/search?q=python&resolve=true")

    assert response.status_code == 200
    assert response.json() == {}
 
 
def test_search_with_resolve_returns_account(client):
    with patch("profed.components.api.c2s.v1.search.resolvers.accounts.lookup_actor_url",
               AsyncMock(return_value="https://mastodon.social/users/alice")):
        with patch("profed.components.api.c2s.v1.search.resolvers.accounts.http") as mock_http:
            mock_http.return_value.json = AsyncMock(return_value=ACTOR)
            response = client.get("/search?q=@alice@mastodon.social&resolve=true")

    assert response.status_code == 200
    result = response.json()
    assert "accounts" in result
    assert len(result["accounts"]) == 1
    assert result["accounts"][0]["acct"] == "alice@mastodon.social"
 
 
def test_search_type_filter_limits_resolvers(client):
    with patch("profed.components.api.c2s.v1.search.resolvers.accounts.lookup_actor_url",
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

