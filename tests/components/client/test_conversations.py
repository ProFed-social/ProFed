# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from unittest.mock import AsyncMock, Mock
 
import httpx
from fastapi import FastAPI
 
from profed.components.client import auth, conversations, templating
 
 
_ENV = templating.build_environment(templating.STANDARD_TEMPLATES, None)
 
 
def _app(monkeypatch):
    monkeypatch.setattr(conversations, "environment", lambda: _ENV)
 
    app = FastAPI()
    app.include_router(conversations.router)
 
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
 
 
def _login(monkeypatch, username="christof", token="tok"):
    session = {"username": username, "acct": f"{username}@test.local", "token": token}
    monkeypatch.setattr(auth, "current_user_optional", AsyncMock(return_value=session))
 
 
def _status(id="1", content="hello", created_at="2026-07-15T10:00:00Z"):
    return {"id": id,
            "content": f"<p>{content}</p>",
            "created_at": created_at,
            "reblogs_count": 0,
            "favourites_count": 0,
            "visibility": "direct",
            "in_reply_to_id": None,
            "reblog": None,
            "uri": f"https://remote.example/{id}",
            "url": f"https://remote.example/{id}",
            "account": {"url": "https://remote.example/@bob",
                        "acct": "bob@remote.example",
                        "username": "bob",
                        "display_name": "Bob",
                        "avatar": None}}
 
 
def _conversation():
    return {"id": "42",
            "unread": True,
            "accounts": [{"username": "bob", "display_name": "Bob"}],
            "last_status": {"content": "<p>last message here</p>",
                            "created_at": "2026-07-15T10:00:00Z"}}


def _api(monkeypatch, conversations_list, root=None, context=None):
    async def get(path, **kwargs):
        if path == "/api/v1/conversations":
            return _resp(200, conversations_list)
        if path.endswith("/context"):
            return _resp(200, context if context is not None else {"ancestors": [], "descendants": []})
        return _resp(200, root)
    monkeypatch.setattr(conversations, "api_client", lambda: Mock(get=AsyncMock(side_effect=get)))
 
 
async def test_conversation_list_redirects_an_anonymous_visitor_to_login(monkeypatch):
    response = await _fetch(_app(monkeypatch), "/conversations")
 
    assert response.status_code == 303
    assert response.headers["location"].startswith("/login?next=")
 
 
async def test_conversation_list_lists_the_users_conversations(monkeypatch):
    _login(monkeypatch)
    _api(monkeypatch, [_conversation()], root=_status("42"))

    response = await _fetch(_app(monkeypatch), "/conversations")
 
    assert response.status_code == 200
    body = response.text
    assert "Bob" in body
    assert "last message here" in body
    assert "/conversations/42" in body
 
 
async def test_conversation_list_without_conversations_says_so(monkeypatch):
    _login(monkeypatch)
    _api(monkeypatch, [])
 
    response = await _fetch(_app(monkeypatch), "/conversations")
 
    assert response.status_code == 200
    assert "No conversations yet" in response.text
 
 
async def test_conversation_shows_root_and_descendants_sorted_by_time(monkeypatch):
    _login(monkeypatch)
    root = _status("10", "the root message", "2026-07-15T10:00:00Z")
    context = {"ancestors": [], "descendants": [_status("11", "a later reply", "2026-07-15T10:05:00Z")]}
 
    _api(monkeypatch, [_conversation()], root=root, context=context)
 
    response = await _fetch(_app(monkeypatch), "/conversations/42")
 
    assert response.status_code == 200
    body = response.text
    assert "the root message" in body and "a later reply" in body
    assert body.index("the root message") < body.index("a later reply")


async def test_conversation_list_opens_the_topmost_conversation(monkeypatch):
    _login(monkeypatch)
    _api(monkeypatch, [_conversation()], root=_status("42", "topmost body"))
 
    response = await _fetch(_app(monkeypatch), "/conversations")
 
    assert response.status_code == 200
    body = response.text
    assert "conversations-layout" in body
    assert "topmost body" in body

