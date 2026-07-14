# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from unittest.mock import AsyncMock, Mock, patch
from profed.components.client import profile


@pytest.fixture(autouse=True)
def standalone_env():
    from pathlib import Path
    from jinja2 import Environment, FileSystemLoader
    templates = Path(profile.__file__).parent / "templates"
    env = Environment(loader=FileSystemLoader(str(templates)), autoescape=True)
    with patch.object(profile, "environment", lambda: env):
        yield


def _resp(status=200, json_data=None):
    r = Mock()
    r.status_code = status
    r.json = Mock(return_value=json_data)
    r.raise_for_status = Mock()
    return r


@pytest.mark.asyncio
async def test_relationship_returns_first_with_token():
    client = Mock(get=AsyncMock(return_value=_resp(200, [{"id": "5", "following": True,
                                                          "requested": False}])))
    with patch.object(profile, "api_client", return_value=client):
        rel = await profile._relationship("5", "tok")
    assert rel["following"] is True
    assert client.get.call_args.kwargs["token"] == "tok"
    assert client.get.call_args.kwargs["params"] == {"id[]": "5"}


@pytest.mark.asyncio
async def test_relationship_empty_returns_none():
    client = Mock(get=AsyncMock(return_value=_resp(200, [])))
    with patch.object(profile, "api_client", return_value=client):
        assert await profile._relationship("5", "tok") is None


@pytest.mark.asyncio
async def test_relationship_error_returns_none():
    client = Mock(get=AsyncMock(return_value=_resp(500, None)))
    with patch.object(profile, "api_client", return_value=client):
        assert await profile._relationship("5", "tok") is None


def test_follow_button_following_renders_unfollow():
    html = profile._follow_button("bob@remote.example", {"following": True, "requested": False})
    assert "Entfolgen" in html
    assert "/@bob@remote.example/unfollow" in html


def test_follow_button_requested_renders_requested():
    html = profile._follow_button("bob@remote.example", {"following": False, "requested": True})
    assert "Angefragt" in html
    assert "/unfollow" in html


def test_follow_button_none_renders_follow():
    html = profile._follow_button("bob@remote.example", {"following": False, "requested": False})
    assert "Folgen" in html
    assert "/@bob@remote.example/follow" in html


@pytest.mark.asyncio
async def test_follow_action_posts_with_token_and_renders_button():
    client = Mock()
    client.get = AsyncMock(return_value=_resp(200, {"id": "5", "acct": "bob@remote.example"}))
    client.post = AsyncMock(return_value=_resp(200, {"following": False, "requested": True}))
    with patch.object(profile, "api_client", return_value=client):
        response = await profile._follow_action("bob@remote.example", "follow", "tok")
    assert client.post.call_args[0][0] == "/api/v1/accounts/5/follow"
    assert client.post.call_args.kwargs["token"] == "tok"
    assert b"Angefragt" in response.body


def test_viewing_other_true_for_different_acct():
    assert profile._viewing_other({"acct": "bob@remote.example"},
                                  {"acct": "alice@example.com", "token": "t"}) is True


def test_viewing_other_false_for_self():
    assert profile._viewing_other({"acct": "alice@example.com"},
                                  {"acct": "alice@example.com", "token": "t"}) is False


def test_viewing_other_false_when_not_logged_in():
    assert profile._viewing_other({"acct": "bob@remote.example"}, None) is False

