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


def _resp(status=200, json_data=None, following=None):
    r = Mock()
    r.status_code = status
    r.json = Mock(return_value=json_data)
    r.text = ""
    r.headers = ({"Link": f'<https://test.local/api/v1/bookmarks?{following}>; rel="next"'}
                 if following else
                 {})
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

    client.get.assert_awaited_once_with("/api/v1/bookmarks", params="limit=20", token="tok")


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


async def test_the_page_offers_to_load_more_when_another_page_follows(monkeypatch):
    _login(monkeypatch)
    response = _resp(200, [_status()], following="limit=20&max_id=400")
    monkeypatch.setattr(bookmarks, "api_client", lambda: Mock(get=AsyncMock(return_value=response)))

    body = (await _fetch(_app(monkeypatch), "/bookmarks")).text

    assert 'hx-get="/bookmarks/more?following=limit%3D20%26max_id%3D400"' in body
    assert 'hx-trigger="revealed"' in body


async def test_the_last_page_offers_nothing_more(monkeypatch):
    _login(monkeypatch)
    monkeypatch.setattr(bookmarks, "api_client", lambda: Mock(get=AsyncMock(return_value=_resp(200, [_status()]))))

    assert "/bookmarks/more" not in (await _fetch(_app(monkeypatch), "/bookmarks")).text


async def test_more_hands_the_query_back_to_the_api_unchanged(monkeypatch):
    _login(monkeypatch)
    client = Mock(get=AsyncMock(return_value=_resp(200, [])))
    monkeypatch.setattr(bookmarks, "api_client", lambda: client)

    await _fetch(_app(monkeypatch), "/bookmarks/more?following=limit%3D20%26max_id%3D400")

    assert client.get.call_args.kwargs["params"] == "limit=20&max_id=400"


async def test_more_renders_only_the_entries(monkeypatch):
    _login(monkeypatch)
    monkeypatch.setattr(bookmarks, "api_client", lambda: Mock(get=AsyncMock(return_value=_resp(200, [_status()]))))

    body = (await _fetch(_app(monkeypatch), "/bookmarks/more?following=limit%3D20")).text

    assert "a post worth keeping" in body
    assert "<html" not in body

