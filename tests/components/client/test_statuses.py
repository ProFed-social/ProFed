# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import AsyncMock, Mock

import httpx
from fastapi import FastAPI

from profed.components.client import auth, statuses


def _app():
    app = FastAPI()
    app.include_router(statuses.router)

    return app


async def _delete(app, path):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://test.local") as client:
        return await client.delete(path)


def _resp(status=200):
    r = Mock()
    r.status_code = status
    r.text = ""
    return r


def _login(monkeypatch, token="tok"):
    monkeypatch.setattr(auth, "current_user_optional",
                        AsyncMock(return_value={"username": "christof",
                                                "acct": "christof@test.local",
                                                "token": token}))


async def test_delete_status_calls_the_api_with_the_session_token(monkeypatch):
    _login(monkeypatch)
    client = Mock(request=AsyncMock(return_value=_resp(200)))
    monkeypatch.setattr(statuses, "api_client", lambda: client)

    await _delete(_app(), "/statuses/424242")

    assert client.request.call_args.args == ("DELETE", "/api/v1/statuses/424242")
    assert client.request.call_args.kwargs["token"] == "tok"


async def test_delete_status_returns_an_empty_fragment(monkeypatch):
    _login(monkeypatch)
    monkeypatch.setattr(statuses, "api_client", lambda: Mock(request=AsyncMock(return_value=_resp(200))))

    response = await _delete(_app(), "/statuses/424242")

    assert response.status_code == 200
    assert response.text == ""


async def test_delete_status_reports_an_api_failure(monkeypatch):
    _login(monkeypatch)
    monkeypatch.setattr(statuses, "api_client", lambda: Mock(request=AsyncMock(return_value=_resp(404))))

    response = await _delete(_app(), "/statuses/424242")

    assert response.status_code == 404


async def test_delete_status_redirects_an_anonymous_visitor_to_login(monkeypatch):
    client = Mock(request=AsyncMock())
    monkeypatch.setattr(statuses, "api_client", lambda: client)

    response = await _delete(_app(), "/statuses/424242")

    assert response.status_code == 401
    assert response.headers["HX-Redirect"].startswith("/login?next=")
    client.request.assert_not_awaited()

