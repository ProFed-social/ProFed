# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from starlette.testclient import TestClient

from profed.components.client import auth


CLIENT_CFG = {"client": {"client_id": "cid", "client_secret": "csecret"}}


def _app():
    app = FastAPI()
    app.include_router(auth.router)
    return app


def _response(status=200, json_data=None):
    response = MagicMock()
    response.status_code = status
    response.text = ""
    response.json = MagicMock(return_value=json_data or {})
    response.raise_for_status = MagicMock()
    return response


async def test_current_user_optional_returns_session():
    request = MagicMock()
    request.cookies = {"session": "sid1"}
    kv = MagicMock()
    kv.get = AsyncMock(return_value={"username": "alice", "token": "t"})

    with patch("profed.components.client.auth.key_value_store", return_value=kv):
        assert await auth.current_user_optional(request) == {"username": "alice", "token": "t"}

    assert kv.get.await_args.args[0] == "client:session:sid1"


async def test_current_user_optional_without_cookie_returns_none():
    request = MagicMock()
    request.cookies = {}

    assert await auth.current_user_optional(request) is None


def test_login_redirects_to_authorize_and_sets_state_cookie():
    with patch("profed.components.client.auth.config", new=lambda: CLIENT_CFG), \
         patch("profed.components.client.auth.domain", new=lambda: "example.test"):
        response = TestClient(_app()).get("/login", follow_redirects=False)

    assert response.status_code == 302
    location = response.headers["location"]
    assert location.startswith("/oauth/authorize?")
    assert "client_id=cid" in location
    assert "redirect_uri=https%3A%2F%2Fexample.test%2Fauth%2Fcallback" in location
    assert response.cookies.get("oauth_state") is not None


def test_callback_rejects_state_mismatch():
    client = TestClient(_app())
    client.cookies.set("oauth_state", "other")

    with patch("profed.components.client.auth.config", new=lambda: CLIENT_CFG):
        response = client.get("/auth/callback?code=c&state=s", follow_redirects=False)

    assert response.status_code == 400


def test_callback_exchanges_token_and_creates_session():
    api = MagicMock()
    api.post = AsyncMock(return_value=_response(200, {"access_token": "acc-tok"}))
    api.get = AsyncMock(return_value=_response(200, {"username": "alice"}))
    kv = MagicMock()
    kv.set = AsyncMock()

    client = TestClient(_app())
    client.cookies.set("oauth_state", "s")

    with patch("profed.components.client.auth.config", new=lambda: CLIENT_CFG), \
         patch("profed.components.client.auth.api_client", return_value=api), \
         patch("profed.components.client.auth.key_value_store", return_value=kv):
        response = client.get("/auth/callback?code=the-code&state=s", follow_redirects=False)

    assert response.status_code == 303
    assert api.post.await_args.args[0] == "/oauth/token"
    assert api.post.await_args.kwargs["data"]["code"] == "the-code"
    assert api.get.await_args.kwargs["token"] == "acc-tok"
    assert kv.set.await_args.args[0].startswith("client:session:")
    assert kv.set.await_args.args[1] == {"username": "alice", "token": "acc-tok"}
    assert response.cookies.get("session") is not None


def test_callback_fails_when_token_exchange_fails():
    api = MagicMock()
    api.post = AsyncMock(return_value=_response(401, {}))
    kv = MagicMock()
    kv.set = AsyncMock()

    client = TestClient(_app())
    client.cookies.set("oauth_state", "s")

    with patch("profed.components.client.auth.config", new=lambda: CLIENT_CFG), \
         patch("profed.components.client.auth.api_client", return_value=api), \
         patch("profed.components.client.auth.key_value_store", return_value=kv):
        response = client.get("/auth/callback?code=c&state=s", follow_redirects=False)

    assert response.status_code == 502
    kv.set.assert_not_awaited()


def test_logout_deletes_session_and_clears_cookie():
    kv = MagicMock()
    kv.delete = AsyncMock()

    client = TestClient(_app())
    client.cookies.set("session", "sid1")

    with patch("profed.components.client.auth.key_value_store", return_value=kv):
        response = client.get("/logout", follow_redirects=False)

    assert response.status_code == 303
    assert kv.delete.await_args.args[0] == "client:session:sid1"

