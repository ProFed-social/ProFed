# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import AsyncMock, Mock

import httpx
from fastapi import FastAPI

from profed.components.client import auth, bookmarks, templating


_ENV = templating.build_environment(templating.STANDARD_TEMPLATES, None)


def _app(monkeypatch):
    monkeypatch.setattr(bookmarks, "environment", lambda: _ENV)
    monkeypatch.setattr(templating, "domain", lambda: "test.local")

    app = FastAPI()
    app.include_router(bookmarks.router)

    return app


async def _fetch(app, path):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://test.local") as client:
        return await client.get(path)


def _resp(status=200, json_data=None):
    r = Mock()
    r.status_code = status
    r.json = Mock(return_value=json_data)
    r.text = ""
    return r


def _status(content="a post worth keeping"):
    return {"id": "1",
            "content": content,
            "created_at": "2026-07-15T10:00:00Z",
            "reblogs_count": 0,
            "favourites_count": 0,
            "bookmarked": True,
            "account": {"url": "https://remote.example/@bob",
                        "acct": "bob@remote.example",
                        "username": "bob",
                        "display_name": "Bob",
                        "avatar": None}}


def _login(monkeypatch, username="christof", token="tok"):
    monkeypatch.setattr(auth, "current_user_optional",
                        AsyncMock(return_value={"username": username,
                                                "acct": f"{username}@test.local",
                                                "token": token}))


async def test_the_page_redirects_an_anonymous_visitor_to_login(monkeypatch):
    response = await _fetch(_app(monkeypatch), "/bookmarks")

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login?next=")


async def test_the_page_asks_the_api_with_the_session_token(monkeypatch):
    _login(monkeypatch)
    client = Mock(get=AsyncMock(return_value=_resp(200, [])))
    monkeypatch.setattr(bookmarks, "api_client", lambda: client)

    await _fetch(_app(monkeypatch), "/bookmarks")

    client.get.assert_awaited_once_with("/api/v1/bookmarks", params={"limit": 20}, token="tok")


async def test_a_kept_post_is_shown(monkeypatch):
    _login(monkeypatch)
    monkeypatch.setattr(bookmarks, "api_client", lambda: Mock(get=AsyncMock(return_value=_resp(200, [_status()]))))

    response = await _fetch(_app(monkeypatch), "/bookmarks")

    assert "a post worth keeping" in response.text
    assert 'hx-post="/statuses/1/unbookmark"' in response.text


async def test_an_empty_list_says_so(monkeypatch):
    _login(monkeypatch)
    monkeypatch.setattr(bookmarks, "api_client", lambda: Mock(get=AsyncMock(return_value=_resp(200, []))))

    response = await _fetch(_app(monkeypatch), "/bookmarks")

    assert "not bookmarked anything yet" in response.text


async def test_a_failing_api_leaves_the_page_standing(monkeypatch):
    _login(monkeypatch)
    monkeypatch.setattr(bookmarks, "api_client", lambda: Mock(get=AsyncMock(return_value=_resp(503, None))))

    response = await _fetch(_app(monkeypatch), "/bookmarks")

    assert response.status_code == 200
    assert "not bookmarked anything yet" in response.text

