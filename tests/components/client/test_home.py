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


def _resp(status=200, json_data=None, following=None):
    r = Mock()
    r.status_code = status
    r.json = Mock(return_value=json_data)
    r.text = ""
    r.headers = ({"Link": f'<https://test.local/api/profed/timeline?{following}>; rel="next"'}
                 if following else
                 {})
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


def _block(status):
    return {"parts": [status], "booster": None, "boosted": [], "cursor": "1"}


def _login(monkeypatch, username="christof", token="tok"):
    session = {"username": username, "acct": f"{username}@test.local", "token": token}
    monkeypatch.setattr(auth, "current_user_optional", AsyncMock(return_value=session))


async def test_home_redirects_an_anonymous_visitor_to_login(monkeypatch):
    response = await _fetch(_app(monkeypatch), "/")

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login?next=")


async def test_home_renders_logged_in_nav(monkeypatch):
    _login(monkeypatch)
    monkeypatch.setattr(home, "api_client", lambda: Mock(get=AsyncMock(return_value=_resp(200, []))))

    response = await _fetch(_app(monkeypatch), "/")

    assert response.status_code == 200
    body = response.text
    assert "/@christof" in body and "/settings" in body and "/logout" in body
    assert ">Login</a>" not in body


async def test_home_timeline_is_fetched_with_the_session_token(monkeypatch):
    _login(monkeypatch)
    client = Mock(get=AsyncMock(return_value=_resp(200, [])))
    monkeypatch.setattr(home, "api_client", lambda: client)

    await _fetch(_app(monkeypatch), "/")

    assert client.get.call_args.args[0] == "/api/profed/timeline"
    assert client.get.call_args.kwargs["token"] == "tok"
    assert client.get.call_args.kwargs["params"] == "limit=20"


async def test_home_timeline_failure_yields_no_statuses(monkeypatch):
    _login(monkeypatch)
    monkeypatch.setattr(home, "api_client", lambda: Mock(get=AsyncMock(return_value=_resp(401))))

    body = (await _fetch(_app(monkeypatch), "/")).text

    assert "Your timeline is empty" in body


async def test_home_shows_the_timeline_of_a_logged_in_user(monkeypatch):
    _login(monkeypatch)
    monkeypatch.setattr(home, "api_client",
                        lambda: Mock(get=AsyncMock(return_value=_resp(200, [_block(_status("a federated post"))]))))

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


async def test_home_does_not_touch_the_api_for_an_anonymous_visitor(monkeypatch):
    client = Mock(get=AsyncMock())
    monkeypatch.setattr(home, "api_client", lambda: client)

    await _fetch(_app(monkeypatch), "/")

    client.get.assert_not_awaited()


async def test_home_targets_the_single_thread_part_when_deleting(monkeypatch):
    _login(monkeypatch)
    mine = _status("my own post", acct="christof@test.local")
    block = {"parts": [mine, {**mine, "id": "2", "content": "and more"}],
             "booster": None,
             "boosted": [],
             "cursor": "1"}
    monkeypatch.setattr(home, "api_client", lambda: Mock(get=AsyncMock(return_value=_resp(200, [block]))))

    body = (await _fetch(_app(monkeypatch), "/")).text

    assert body.count('hx-target="closest .entry"') == 2
    assert body.count('class="thread-part entry') == 2
    assert 'hx-delete="/statuses/1"' in body
    assert 'hx-delete="/statuses/2"' in body


async def test_the_page_offers_to_load_more_when_another_page_follows(monkeypatch):
    _login(monkeypatch)
    response = _resp(200, [_block(_status())], following="limit=20&max_id=400")
    monkeypatch.setattr(home, "api_client", lambda: Mock(get=AsyncMock(return_value=response)))

    body = (await _fetch(_app(monkeypatch), "/")).text

    assert 'hx-get="/timeline/more?following=limit%3D20%26max_id%3D400"' in body
    assert 'hx-trigger="revealed"' in body


async def test_the_last_page_offers_nothing_more(monkeypatch):
    _login(monkeypatch)
    monkeypatch.setattr(home, "api_client",
                        lambda: Mock(get=AsyncMock(return_value=_resp(200, [_block(_status())]))))

    assert "/timeline/more" not in (await _fetch(_app(monkeypatch), "/")).text


async def test_more_hands_the_query_back_to_the_api_unchanged(monkeypatch):
    _login(monkeypatch)
    client = Mock(get=AsyncMock(return_value=_resp(200, [])))
    monkeypatch.setattr(home, "api_client", lambda: client)

    await _fetch(_app(monkeypatch), "/timeline/more?following=limit%3D20%26max_id%3D400")

    assert client.get.call_args.kwargs["params"] == "limit=20&max_id=400"


async def test_more_without_a_query_starts_at_the_front(monkeypatch):
    _login(monkeypatch)
    client = Mock(get=AsyncMock(return_value=_resp(200, [])))
    monkeypatch.setattr(home, "api_client", lambda: client)

    await _fetch(_app(monkeypatch), "/timeline/more")

    assert client.get.call_args.kwargs["params"] == "limit=20"


async def test_more_renders_only_the_entries(monkeypatch):
    _login(monkeypatch)
    monkeypatch.setattr(home, "api_client",
                        lambda: Mock(get=AsyncMock(return_value=_resp(200, [_block(_status())]))))

    body = (await _fetch(_app(monkeypatch), "/timeline/more?following=limit%3D20")).text

    assert "hello world" in body
    assert "<html" not in body


async def test_the_loader_shows_that_something_is_happening(monkeypatch):
    _login(monkeypatch)
    response = _resp(200, [_block(_status())], following="limit=20&max_id=400")
    monkeypatch.setattr(home, "api_client", lambda: Mock(get=AsyncMock(return_value=response)))

    body = (await _fetch(_app(monkeypatch), "/")).text

    assert 'class="spinner"' in body
    assert 'role="status"' in body

