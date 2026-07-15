# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import AsyncMock, Mock

import httpx
from fastapi import FastAPI

from profed.components.client import auth, home, templating


_ENV = templating.build_environment(templating.STANDARD_TEMPLATES, None)


def _app(monkeypatch):
    monkeypatch.setattr(home, "environment", lambda: _ENV)

    app = FastAPI()
    app.include_router(home.router)

    return app


async def _fetch(app, path):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://test.local") as client:
        return await client.get(path)


async def test_home_renders_masthead_for_anonymous_visitor(monkeypatch):
    response = await _fetch(_app(monkeypatch), "/")

    assert response.status_code == 200
    body = response.text
    assert "ProFed" in body
    assert "/login?next=" in body
    assert "/settings" not in body and "/logout" not in body


async def test_home_renders_logged_in_nav(monkeypatch):
    monkeypatch.setattr(auth, "current_user_optional",
                        AsyncMock(return_value={"username": "christof", "token": "t"}))

    response = await _fetch(_app(monkeypatch), "/")

    assert response.status_code == 200
    body = response.text
    assert "/@christof" in body and "/settings" in body and "/logout" in body
    assert ">Login</a>" not in body


def _resp(status=200, json_data=None):
    r = Mock()
    r.status_code = status
    r.json = Mock(return_value=json_data)
    r.text = ""
    return r


def _status(content="hello world", acct="bob@remote.example"):
    return {"id": "1",
            "content": content,
            "created_at": "2026-07-15T10:00:00Z",
            "reblogs_count": 0,
            "favourites_count": 0,
            "account": {"url": f"https://remote.example/@{acct.split('@')[0]}",
                        "acct": acct,
                        "username": acct.split("@")[0],
                        "display_name": "Bob",
                        "avatar": None}}


def _login(monkeypatch, username="christof", token="tok"):
    session = {"username": username, "acct": f"{username}@test.local", "token": token}
    monkeypatch.setattr(home, "current_user_optional", AsyncMock(return_value=session))
    monkeypatch.setattr(auth, "current_user_optional", AsyncMock(return_value=session))


async def test_home_timeline_is_fetched_with_the_session_token(monkeypatch):
    client = Mock(get=AsyncMock(return_value=_resp(200, [_status()])))
    monkeypatch.setattr(home, "api_client", lambda: client)

    statuses = await home._home_timeline("tok")

    assert statuses == [_status()]
    assert client.get.call_args.args[0] == "/api/v1/timelines/home"
    assert client.get.call_args.kwargs["token"] == "tok"
    assert client.get.call_args.kwargs["params"] == {"limit": 20}


async def test_home_timeline_failure_yields_no_statuses(monkeypatch):
    monkeypatch.setattr(home, "api_client", lambda: Mock(get=AsyncMock(return_value=_resp(401))))

    assert await home._home_timeline("tok") == []


async def test_home_shows_the_timeline_of_a_logged_in_user(monkeypatch):
    _login(monkeypatch)
    monkeypatch.setattr(home, "api_client",
                        lambda: Mock(get=AsyncMock(return_value=_resp(200, [_status("a federated post")]))))

    response = await _fetch(_app(monkeypatch), "/")

    assert response.status_code == 200
    assert "a federated post" in response.text
    assert "@bob@remote.example" in response.text


async def test_home_of_a_logged_in_user_without_posts_says_so(monkeypatch):
    _login(monkeypatch)
    monkeypatch.setattr(home, "api_client", lambda: Mock(get=AsyncMock(return_value=_resp(200, []))))

    response = await _fetch(_app(monkeypatch), "/")

    assert response.status_code == 200
    assert "Your timeline is empty" in response.text


async def test_home_asks_an_anonymous_visitor_to_log_in(monkeypatch):
    client = Mock(get=AsyncMock())
    monkeypatch.setattr(home, "api_client", lambda: client)

    response = await _fetch(_app(monkeypatch), "/")

    assert response.status_code == 200
    assert "to see your timeline" in response.text
    client.get.assert_not_awaited()

