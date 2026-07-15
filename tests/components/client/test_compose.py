# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import AsyncMock, Mock

import httpx
from fastapi import FastAPI

from profed.components.client import auth, compose, templating


_ENV = templating.build_environment(templating.STANDARD_TEMPLATES, None)


def _app(monkeypatch):
    monkeypatch.setattr(compose, "environment", lambda: _ENV)

    app = FastAPI()
    app.include_router(compose.router)

    return app


async def _post(app, path, data):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://test.local") as client:
        return await client.post(path, data=data)


def _resp(status=200, json_data=None):
    r = Mock()
    r.status_code = status
    r.json = Mock(return_value=json_data)
    r.text = ""
    return r


def _status(content="<p>hello</p>"):
    return {"id": "https://test.local/actors/christof/notes/1",
            "content": content,
            "created_at": "2026-07-16T10:00:00Z",
            "reblogs_count": 0,
            "favourites_count": 0,
            "account": {"url": "https://test.local/@christof",
                        "acct": "christof@test.local",
                        "username": "christof",
                        "display_name": "Christof",
                        "avatar": None}}


def _login(monkeypatch, token="tok"):
    monkeypatch.setattr(auth, "current_user_optional",
                        AsyncMock(return_value={"username": "christof",
                                                "acct": "christof@test.local",
                                                "token": token}))


async def test_compose_posts_the_status_to_the_api(monkeypatch):
    _login(monkeypatch)
    client = Mock(post=AsyncMock(return_value=_resp(200, _status())))
    monkeypatch.setattr(compose, "api_client", lambda: client)

    await _post(_app(monkeypatch), "/compose", {"status": "hello"})

    assert client.post.call_args.args[0] == "/api/v1/statuses"
    assert client.post.call_args.kwargs["json"] == {"status": "hello", "visibility": "public"}
    assert client.post.call_args.kwargs["token"] == "tok"


async def test_compose_returns_the_new_status_as_a_fragment(monkeypatch):
    _login(monkeypatch)
    monkeypatch.setattr(compose, "api_client",
                        lambda: Mock(post=AsyncMock(return_value=_resp(200, _status("<p>a new post</p>")))))

    response = await _post(_app(monkeypatch), "/compose", {"status": "a new post"})

    assert response.status_code == 200
    assert "a new post" in response.text
    assert "h-entry status" in response.text
    assert "<html" not in response.text


async def test_compose_reports_an_api_failure(monkeypatch):
    _login(monkeypatch)
    monkeypatch.setattr(compose, "api_client", lambda: Mock(post=AsyncMock(return_value=_resp(422))))

    response = await _post(_app(monkeypatch), "/compose", {"status": "x" * 6000})

    assert response.status_code == 422


async def test_compose_redirects_an_anonymous_visitor_to_login(monkeypatch):
    client = Mock(post=AsyncMock())
    monkeypatch.setattr(compose, "api_client", lambda: client)

    response = await _post(_app(monkeypatch), "/compose", {"status": "hello"})

    assert response.status_code == 401
    assert response.headers["HX-Redirect"].startswith("/login?next=")
    client.post.assert_not_awaited()

