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


def _login(monkeypatch, username="christof", token="tok"):
    session = {"username": username, "acct": f"{username}@test.local", "token": token}
    monkeypatch.setattr(auth, "current_user_optional", AsyncMock(return_value=session))


def _status(id="1",
            content="hello",
            created_at="2026-07-15T10:00:00Z",
            acct="bob@remote.example",
            username="bob",
            display_name="Bob",
            account_url=None):
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
            "account": {"url": account_url or f"https://remote.example/@{username}",
                        "acct": acct,
                        "username": username,
                        "display_name": display_name,
                        "avatar": None}}


def _conversation(accounts=None):
    return {"id": "42",
            "unread": True,
            "accounts": accounts or [{"username": "bob", "display_name": "Bob"}],
            "last_status": {"content": "<p>last message here</p>",
                            "created_at": "2026-07-15T10:00:00Z"}}


def _api(monkeypatch, conversations_list, messages=None):
    async def get(path, **kwargs):
        if path == "/api/v1/conversations":
            return _resp(200, conversations_list)
        if path.endswith("/messages"):
            return _resp(200, messages if messages is not None else [])
        return _resp(200, None)
    monkeypatch.setattr(conversations, "api_client", lambda: Mock(get=AsyncMock(side_effect=get)))


async def test_conversation_list_redirects_an_anonymous_visitor_to_login(monkeypatch):
    response = await _fetch(_app(monkeypatch), "/conversations")

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login?next=")


async def test_conversation_list_lists_the_users_conversations(monkeypatch):
    _login(monkeypatch)
    _api(monkeypatch, [_conversation()], messages=[_status("42")])

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
    messages = [_status("10", "the root message", "2026-07-15T10:00:00Z"),
                _status("11", "a later reply", "2026-07-15T10:05:00Z")]
    _api(monkeypatch, [_conversation()], messages=messages)

    response = await _fetch(_app(monkeypatch), "/conversations/42")

    assert response.status_code == 200
    body = response.text
    assert "the root message" in body and "a later reply" in body
    assert body.index("the root message") < body.index("a later reply")


async def test_conversation_list_opens_the_topmost_conversation(monkeypatch):
    _login(monkeypatch)
    _api(monkeypatch, [_conversation()], messages=[_status("42", "topmost body")])

    response = await _fetch(_app(monkeypatch), "/conversations")

    assert response.status_code == 200
    body = response.text
    assert "conversations-layout" in body
    assert "topmost body" in body


async def test_conversation_marks_the_logged_in_users_own_messages(monkeypatch):
    _login(monkeypatch)
    messages = [_status("10", "from bob"),
                _status("11",
                        "from me",
                        "2026-07-15T10:05:00Z",
                        acct="christof@example.com",
                        username="christof",
                        display_name="Christof",
                        account_url="https://example.com/actors/christof")]
    _api(monkeypatch, [_conversation()], messages=messages)

    body = (await _fetch(_app(monkeypatch), "/conversations/42")).text

    assert "msg--own" in body
    assert "msg--other" in body


async def test_conversation_groups_consecutive_messages_of_one_author(monkeypatch):
    _login(monkeypatch)
    messages = [_status("10", "first", "2026-07-15T10:00:00Z"),
                _status("11", "second", "2026-07-15T10:05:00Z")]
    _api(monkeypatch, [_conversation()], messages=messages)

    body = (await _fetch(_app(monkeypatch), "/conversations/42")).text

    assert "msg--run-cont" in body


async def test_conversation_reply_posts_a_direct_reply_to_the_root(monkeypatch):
    _login(monkeypatch)
    posted = {}

    async def post(path, json=None, token=None):
        posted.update(path=path, json=json)
        return _resp(200, _status("99"))
    monkeypatch.setattr(conversations, "api_client",
                        lambda: Mock(post=AsyncMock(side_effect=post),
                                     get=AsyncMock(return_value=_resp(200, []))))

    response = await _post(_app(monkeypatch), "/conversations/42/reply", {"status": "hi"})

    assert posted["json"] == {"status": "hi", "in_reply_to_id": "42", "visibility": "direct"}
    assert response.status_code == 200
    assert "conversation-messages" in response.text


async def test_conversation_list_sizes_a_single_avatar_to_the_full_collage(monkeypatch):
    _login(monkeypatch)
    _api(monkeypatch, [_conversation()])
 
    body = (await _fetch(_app(monkeypatch), "/conversations")).text
 
    assert "conversation-avatars--1" in body
 
 
async def test_conversation_list_shows_an_avatar_collage_with_overflow_chip(monkeypatch):
    _login(monkeypatch)
    accounts = [{"username": u, "display_name": u.title()}
                for u in ["anna", "bob", "carla", "dan", "eve"]]
    _api(monkeypatch, [_conversation(accounts=accounts)])
 
    body = (await _fetch(_app(monkeypatch), "/conversations")).text
 
    assert "conversation-avatars--3" in body
    assert "conversation-avatar--more" in body
    assert "+3" in body
    assert "conversation-participants" in body
    for name in ["Anna", "Bob", "Carla", "Dan", "Eve"]:
        assert name in body


def _reply_msg(id, url, content, in_reply_to_id=None, reply_to=None):
    return {"id": id,
            "account": {"acct": url.rsplit("/", 1)[-1], "username": url.rsplit("/", 1)[-1],
                        "display_name": url.rsplit("/", 1)[-1].title(), "url": url},
            "content": f"<p>{content}</p>",
            "in_reply_to_id": in_reply_to_id,
            "reply_to": reply_to}


async def test_conversation_view_omits_the_reply_marking_for_a_self_continuation(monkeypatch):
    _login(monkeypatch)
    preview = {"account": {"username": "bob", "display_name": "Bob", "url": "https://x/bob", "avatar": None},
               "content": "<p>first</p>"}
    messages = [_reply_msg("1", "https://x/bob", "first"),
                _reply_msg("2", "https://x/bob", "second", in_reply_to_id="1", reply_to=preview)]
    _api(monkeypatch, [_conversation()], messages=messages)

    body = (await _fetch(_app(monkeypatch), "/conversations/42")).text

    assert "msg-reply-name" not in body


async def test_conversation_view_shows_the_reply_marking_across_authors(monkeypatch):
    _login(monkeypatch)
    preview = {"account": {"username": "bob", "display_name": "Bob", "url": "https://x/bob", "avatar": None},
               "content": "<p>first</p>"}
    messages = [_reply_msg("1", "https://x/bob", "first"),
                _reply_msg("2", "https://x/alice", "second", in_reply_to_id="1", reply_to=preview)]
    _api(monkeypatch, [_conversation()], messages=messages)

    body = (await _fetch(_app(monkeypatch), "/conversations/42")).text


    assert "msg-reply-name" in body


async def test_conversation_reply_targets_an_explicit_message(monkeypatch):
    _login(monkeypatch)
    posted = {}

    async def post(path, json=None, token=None):
        posted.update(json=json)
        return _resp(200, _status("99"))
    monkeypatch.setattr(conversations, "api_client",
                        lambda: Mock(post=AsyncMock(side_effect=post),
                                     get=AsyncMock(return_value=_resp(200, []))))

    await _post(_app(monkeypatch), "/conversations/42/reply",
                {"status": "hi", "in_reply_to_id": "7"})

    assert posted["json"]["in_reply_to_id"] == "7"


async def test_conversation_view_renders_a_reply_button_with_the_message_id(monkeypatch):
    _login(monkeypatch)
    _api(monkeypatch, [_conversation()], messages=[_reply_msg("7", "https://x/bob", "hallo")])

    body = (await _fetch(_app(monkeypatch), "/conversations/42")).text

    assert "msg-reply-btn" in body
    assert 'data-reply-id="7"' in body
    assert "msg-actions" in body
    assert "disabled" in body

