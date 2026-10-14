# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import AsyncMock, Mock

import httpx
from fastapi import FastAPI

from profed.components.client import auth, statuses, templating


_ENV = templating.build_environment(templating.STANDARD_TEMPLATES, None)


def _app(monkeypatch):
    monkeypatch.setattr(statuses, "environment", lambda: _ENV)
    monkeypatch.setattr(templating, "domain", lambda: "test.local")

    app = FastAPI()
    app.include_router(statuses.router)

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
    r.headers = {}
    return r


def _attachment(name):
    return {"id": f"https://test.local/media/{name}",
            "type": "image",
            "mime_type": "image/jpeg",
            "filename": f"{name}.jpg",
            "url": f"https://test.local/media/{name}",
            "description": name,
            "meta": {"original": {"width": 1280, "height": 720}}}


def _status(attachments=0, acct="alice"):
    return {"id": "1",
            "content": "<p>a post with everything on it</p>",
            "created_at": "2026-07-15T10:00:00Z",
            "url": "https://remote.example/@bob/9",
            "uri": "https://remote.example/users/bob/statuses/9",
            "reblogs_count": 0,
            "favourites_count": 0,
            "media_attachments": [_attachment(f"m{n}") for n in range(attachments)],
            "account": {"url": f"https://test.local/@{acct}",
                        "acct": acct,
                        "username": "alice",
                        "display_name": "Alice",
                        "avatar": None}}


def _login(monkeypatch, username="alice", token="tok"):
    monkeypatch.setattr(auth, "current_user_optional",
                        AsyncMock(return_value={"username": username,
                                                "acct": f"{username}@test.local",
                                                "token": token}))


async def test_the_page_redirects_an_anonymous_visitor_to_login(monkeypatch):
    response = await _fetch(_app(monkeypatch), "/statuses/1")

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login?next=")


async def test_the_page_asks_the_api_with_the_session_token(monkeypatch):
    _login(monkeypatch)
    client = Mock(get=AsyncMock(return_value=_resp(200, _status())))
    monkeypatch.setattr(statuses, "api_client", lambda: client)

    await _fetch(_app(monkeypatch), "/statuses/1")

    client.get.assert_awaited_once_with("/api/v1/statuses/1", token="tok")


async def test_the_page_shows_the_post(monkeypatch):
    _login(monkeypatch)
    monkeypatch.setattr(statuses, "api_client", lambda: Mock(get=AsyncMock(return_value=_resp(200, _status()))))

    response = await _fetch(_app(monkeypatch), "/statuses/1")

    assert response.status_code == 200
    assert "a post with everything on it" in response.text


async def test_the_page_shows_every_attachment_without_a_budget(monkeypatch):
    _login(monkeypatch)
    many = _status(attachments=10)
    monkeypatch.setattr(statuses, "api_client", lambda: Mock(get=AsyncMock(return_value=_resp(200, many))))

    body = (await _fetch(_app(monkeypatch), "/statuses/1")).text

    assert "media-more" not in body
    for n in range(10):
        assert f"https://test.local/media/m{n}" in body


def test_the_timeline_still_cuts_the_same_post_off():
    body = _ENV.get_template("status.html").render(status=_status(attachments=10))

    assert "media-more" in body
    assert "https://test.local/media/m9" not in body


async def test_the_page_offers_to_reply(monkeypatch):
    _login(monkeypatch)
    monkeypatch.setattr(statuses, "api_client", lambda: Mock(get=AsyncMock(return_value=_resp(200, _status()))))

    body = (await _fetch(_app(monkeypatch), "/statuses/1")).text

    assert 'class="action respond reply-trigger"' in body
    assert 'data-reply-id="1"' in body


async def test_a_status_the_api_does_not_know_is_not_found(monkeypatch):
    _login(monkeypatch)
    monkeypatch.setattr(statuses, "api_client", lambda: Mock(get=AsyncMock(return_value=_resp(404, None))))

    response = await _fetch(_app(monkeypatch), "/statuses/1")

    assert response.status_code == 404

