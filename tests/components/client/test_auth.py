# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI, Request
from starlette.testclient import TestClient

from profed.components.client import auth


CLIENT_CFG = {"client": {"client_id": "cid",
                         "client_secret": "csecret",
                         "scope": "read write",
                         "session_ttl": 86400,
                         "cookie_secure": True}}

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


def _callback(api, kv):
    client = TestClient(_app())
    client.cookies.set("oauth_state", "s")

    with patch("profed.components.client.auth.config", new=lambda: CLIENT_CFG), \
         patch("profed.components.client.auth.api_client", return_value=api), \
         patch("profed.components.client.auth.key_value_store", return_value=kv):
        return client.get("/auth/callback?code=the-code&state=s", follow_redirects=False)


def _logging_in(history=None):
    api = MagicMock()
    api.post = AsyncMock(return_value=_response(200, {"access_token": "acc-tok"}))
    api.get = AsyncMock(side_effect=[_response(200, {"username": "alice", "acct": "alice@example.com"}),
                                     _response(200, history if history is not None else {"counts": [],
                                                                                         "last_toned": None})])
    return api


def test_callback_exchanges_token_and_creates_session():
    api = _logging_in()
    kv = MagicMock()
    kv.set = AsyncMock()

    response = _callback(api, kv)

    assert response.status_code == 303
    assert api.post.await_args.args[0] == "/oauth/token"
    assert api.post.await_args.kwargs["data"]["code"] == "the-code"
    assert api.get.await_args_list[0].kwargs["token"] == "acc-tok"
    assert kv.set.await_args.args[0].startswith("client:session:")
    assert kv.set.await_args.args[1] == {"username": "alice",
                                         "acct": "alice@example.com",
                                         "token": "acc-tok",
                                         "reactions": {},
                                         "tone": ""}
    assert response.cookies.get("session") is not None


def test_a_new_session_carries_the_reaction_history():
    api = _logging_in({"counts": [{"emoji": "\U0001F44D", "n_of_uses": 2},
                                  {"emoji": "\U0001F44D\U0001F3FD", "n_of_uses": 3},
                                  {"emoji": "\U0001F389", "n_of_uses": 1}],
                       "last_toned": "\U0001F44D\U0001F3FD"})
    kv = MagicMock()
    kv.set = AsyncMock()

    _callback(api, kv)

    assert api.get.await_args_list[1].args[0] == "/api/profed/reactions/history"
    assert kv.set.await_args.args[1]["reactions"] == {"\U0001F44D": 5, "\U0001F389": 1}
    assert kv.set.await_args.args[1]["tone"] == "medium"


def test_a_failing_reaction_history_does_not_stop_the_login():
    unavailable = _response(503)
    unavailable.json = MagicMock(side_effect=ValueError("no json"))
    api = _logging_in()
    api.get = AsyncMock(side_effect=[_response(200, {"username": "alice", "acct": "alice@example.com"}),
                                     unavailable])
    kv = MagicMock()
    kv.set = AsyncMock()

    assert _callback(api, kv).status_code == 303
    assert kv.set.await_args.args[1]["reactions"] == {}
    assert kv.set.await_args.args[1]["tone"] == ""


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


def test_safe_next_accepts_local_paths():
    assert auth._safe_next("/settings") == "/settings"
    assert auth._safe_next("/@alice/sub/path") == "/@alice/sub/path"


def test_safe_next_rejects_offsite_and_loop_targets():
    assert auth._safe_next(None) == "/"
    assert auth._safe_next("") == "/"
    assert auth._safe_next("//evil.example") == "/"
    assert auth._safe_next("/\\evil.example") == "/"
    assert auth._safe_next("https://evil.example") == "/"
    assert auth._safe_next("/login") == "/"
    assert auth._safe_next("/login?next=/x") == "/"


def test_login_carries_validated_next_in_return_cookie():
    with patch("profed.components.client.auth.config", new=lambda: CLIENT_CFG), \
         patch("profed.components.client.auth.domain", new=lambda: "example.test"):
        response = TestClient(_app()).get("/login?next=/settings", follow_redirects=False)

    assert response.status_code == 302
    assert response.cookies.get("oauth_return").strip('"') == "/settings"   # cookie-quoted by set_cookie


def test_login_ignores_offsite_next():
    with patch("profed.components.client.auth.config", new=lambda: CLIENT_CFG), \
         patch("profed.components.client.auth.domain", new=lambda: "example.test"):
        response = TestClient(_app()).get("/login?next=//evil.example", follow_redirects=False)

    assert response.cookies.get("oauth_return") is None


def _callback_client(return_target):
    api = MagicMock()
    api.post = AsyncMock(return_value=_response(200, {"access_token": "acc-tok"}))
    api.get = AsyncMock(return_value=_response(200, {"username": "alice", "acct": "alice@example.com"}))
    kv = MagicMock()
    kv.set = AsyncMock()

    client = TestClient(_app())
    client.cookies.set("oauth_state", "s")
    client.cookies.set("oauth_return", return_target)
    return client, api, kv


def test_callback_redirects_to_return_target():
    client, api, kv = _callback_client("/settings")

    with patch("profed.components.client.auth.config", new=lambda: CLIENT_CFG), \
         patch("profed.components.client.auth.api_client", return_value=api), \
         patch("profed.components.client.auth.key_value_store", return_value=kv):
        response = client.get("/auth/callback?code=c&state=s", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/settings"


def test_callback_rejects_tampered_return_target():
    client, api, kv = _callback_client("//evil.example")

    with patch("profed.components.client.auth.config", new=lambda: CLIENT_CFG), \
         patch("profed.components.client.auth.api_client", return_value=api), \
         patch("profed.components.client.auth.key_value_store", return_value=kv):
        response = client.get("/auth/callback?code=c&state=s", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/"



def _protected_app():
    app = FastAPI()

    @app.get("/secret")
    @auth.requires_login
    async def secret(request: Request, session):
        return session["username"]

    @app.post("/secret")
    @auth.requires_login
    async def secret_post(request: Request, session):
        return "ok"

    return app


def _guard(session):
    async def _user(request):
        return session

    return _user


def test_requires_login_redirects_get_to_login_with_encoded_next():
    with patch("profed.components.client.auth.current_user_optional", _guard(None)):
        response = TestClient(_protected_app()).get("/secret?tab=x", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login?next=%2Fsecret%3Ftab%3Dx"


def test_requires_login_returns_401_hx_redirect_for_non_get():
    with patch("profed.components.client.auth.current_user_optional", _guard(None)):
        response = TestClient(_protected_app()).post("/secret", follow_redirects=False)

    assert response.status_code == 401
    assert response.headers["HX-Redirect"] == "/login?next=%2Fsecret"


def test_requires_login_passes_session_to_handler():
    with patch("profed.components.client.auth.current_user_optional",
               _guard({"username": "alice", "token": "t"})):
        response = TestClient(_protected_app()).get("/secret", follow_redirects=False)

    assert response.status_code == 200
    assert response.json() == "alice"


async def test_page_context_anonymous_carries_login_url_with_current_path():
    request = MagicMock()
    request.cookies = {}
    request.url.path = "/@christof"
    request.url.query = ""

    ctx = await auth.page_context(request)

    assert ctx["current_username"] is None
    assert ctx["login_url"] == "/login?next=%2F%40christof"


async def test_page_context_reports_logged_in_username():
    request = MagicMock()
    request.cookies = {"session": "sid1"}
    request.url.path = "/@christof"
    request.url.query = ""
    kv = MagicMock()
    kv.get = AsyncMock(return_value={"username": "christof", "token": "t"})

    with patch("profed.components.client.auth.key_value_store", return_value=kv):
        ctx = await auth.page_context(request)

    assert ctx["current_username"] == "christof"


async def test_save_session_writes_the_session_back_under_its_own_key():
    request = MagicMock()
    request.cookies = {"session": "sid1"}
    kv = MagicMock()
    kv.set = AsyncMock()

    with patch("profed.components.client.auth.config", new=lambda: CLIENT_CFG), \
         patch("profed.components.client.auth.key_value_store", return_value=kv):
        await auth.save_session(request, {"username": "alice", "tone": "medium"})

    assert kv.set.await_args.args == ("client:session:sid1", {"username": "alice", "tone": "medium"}, 86400)


async def test_save_session_without_a_cookie_writes_nothing():
    request = MagicMock()
    request.cookies = {}
    kv = MagicMock()
    kv.set = AsyncMock()

    with patch("profed.components.client.auth.key_value_store", return_value=kv):
        await auth.save_session(request, {"username": "alice"})

    kv.set.assert_not_awaited()

