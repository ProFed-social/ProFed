# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import time
import re
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from profed.core import message_bus
from profed.components.api.c2s.oauth import router as oauth_router_module
from profed.components.api.c2s.oauth import projection
 
 
CONFIG = {"oidc_issuer":      "https://cloud.example.com/",
          "oidc_client_id":  "profed",
          "oidc_client_secret": "secret",
          "oidc_callback_url": "https://profed.example.com/oauth/callback"}
 
APP = {"client_id":     "abc123",
       "client_secret": "appsecret",
       "client_name":   "TestApp",
       "redirect_uris": "https://app.example.com/callback",
       "scopes":        "read write"}
 
 
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
    oauth_router_module.init(CONFIG)
    app = FastAPI()
    app.include_router(oauth_router_module.router)
    return TestClient(app, follow_redirects=False)
 
 
def test_authorize_unknown_client_returns_401(client):
    with patch("profed.components.api.c2s.oauth.router.get_app", return_value=None):
        response = client.get("/oauth/authorize"
                              "?response_type=code"
                              "&client_id=unknown"
                              "&redirect_uri=https://app.example.com/callback")
    assert response.status_code == 401
 
 
def test_authorize_invalid_redirect_uri_returns_400(client):
    with patch("profed.components.api.c2s.oauth.router.get_app", return_value=APP):
        response = client.get("/oauth/authorize"
                              "?response_type=code"
                              "&client_id=abc123"
                              "&redirect_uri=https://evil.example.com/callback")
    assert response.status_code == 400
 
 
def test_authorize_redirects_to_nextcloud(client):
    with patch("profed.components.api.c2s.oauth.router.get_app", return_value=APP), \
         patch("profed.components.api.c2s.oauth.router.authorization_url",
               new=AsyncMock(return_value="https://cloud.example.com/authorize")):\
        response = client.get("/oauth/authorize"
                              "?response_type=code"
                              "&client_id=abc123"
                              "&redirect_uri=https://app.example.com/callback")
    assert response.status_code == 307
    assert response.headers["location"] == "https://cloud.example.com/authorize"
 
 
def test_callback_invalid_state_returns_400(client):
    response = client.get("/oauth/callback?code=nc_code&state=unknown_state")
    assert response.status_code == 400
 
 
def test_token_invalid_client_returns_401(client):
    with patch("profed.components.api.c2s.oauth.router.get_app", return_value=None):
        response = client.post("/oauth/token",
                               data={"grant_type":    "authorization_code",
                                     "code":          "somecode",
                                     "client_id":     "unknown",
                                     "client_secret": "wrong"})
    assert response.status_code == 401
 
 
def test_token_invalid_code_returns_400(client):
    with patch("profed.components.api.c2s.oauth.router.get_app", return_value=APP), \
         patch("profed.components.api.c2s.oauth.router.get_code", return_value=None):
        response = client.post("/oauth/token",
                               data={"grant_type":    "authorization_code",
                                     "code":          "badcode",
                                     "client_id":     "abc123",
                                     "client_secret": "appsecret"})
    assert response.status_code == 400
 
 
def test_token_success_returns_access_token(client, fake_bus):
    code_entry = {"code":       "mycode",
                  "client_id":  "abc123",
                  "username":   "alice",
                  "id_token":   "the_jwt",
                  "expires_at": time.time() + 600}
    with patch("profed.components.api.c2s.oauth.router.get_app", return_value=APP), \
         patch("profed.components.api.c2s.oauth.router.get_code", return_value=code_entry), \
         patch("profed.components.api.c2s.oauth.router.consume_code",
               new=AsyncMock()):
        response = client.post("/oauth/token",
                               data={"grant_type":    "authorization_code",
                                     "code":          "mycode",
                                     "client_id":     "abc123",
                                     "client_secret": "appsecret"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["access_token"], str)
    assert re.fullmatch("[a-zA-Z0-9_-]*", data["access_token"])
    assert data["token_type"] == "Bearer"

