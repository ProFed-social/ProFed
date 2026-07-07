# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging

import httpx
from fastapi import FastAPI
from jinja2 import Environment, select_autoescape

from profed.components.client import profile, templating


_ENV = Environment(loader=templating.build_loader(templating.STANDARD_TEMPLATES, None),
                   autoescape=select_autoescape(["html", "xml"]))


def _resp(status_code, **kwargs):
    return httpx.Response(status_code,
                          request=httpx.Request("GET", "https://test.local/api"),
                          **kwargs)


class _FakeClient:
    def __init__(self, responses):
        self._responses = responses

    async def get(self, path, **kwargs):
        for marker, response in self._responses.items():
            if marker in path:
                return response

        return _resp(404)


def _app(monkeypatch, responses):
    monkeypatch.setattr(profile, "api_client", lambda: _FakeClient(responses))
    monkeypatch.setattr(profile, "environment", lambda: _ENV)

    app = FastAPI()
    app.include_router(profile.router)

    return app


def _account():
    return {"id": "1",
            "username": "alice",
            "acct": "alice@example.test",
            "display_name": "Alice",
            "note": "<p>hi</p>",
            "url": "https://example.test/@alice",
            "avatar": None,
            "header": None,
            "statuses_count": 2,
            "following_count": 5,
            "followers_count": 7,
            "created_at": "2026-01-15T10:00:00+00:00",
            "resume": {"experience": [{"name": "Engineer",
                                       "organization": "Acme",
                                       "start": "2020",
                                       "end": "2024",
                                       "description": "Built things"}],
                       "education": [],
                       "projects": [{"name": "Demo",
                                     "description": "<p>A <b>cool</b> project</p>"
                                                    "<script>steal()</script>"}],
                       "skills": [{"name": "Python"}]}}


def _posts():
    return [{"id": "10",
             "content": "<p>first post</p>",
             "created_at": "2026-02-01T09:00:00+00:00",
             "reblogs_count": 1,
             "favourites_count": 3},
            {"id": "11",
             "content": "<p>second</p>",
             "created_at": "2026-02-02T09:00:00+00:00",
             "reblogs_count": 0,
             "favourites_count": 0}]


async def _fetch(app, path):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://test.local") as client:
        return await client.get(path)


async def test_profile_renders_header_cv_and_posts(monkeypatch):
    app = _app(monkeypatch, {"lookup": _resp(200, json=_account()),
                             "statuses": _resp(200, json=_posts())})

    response = await _fetch(app, "/@alice")

    assert response.status_code == 200
    body = response.text
    assert "Alice" in body
    assert "@alice@example.test" in body
    assert "<p>hi</p>" in body
    assert "Engineer" in body and "Acme" in body
    assert "Python" in body
    assert "<p>first post</p>" in body
    assert "<p>A <b>cool</b> project</p>" in body
    assert "steal()" not in body
    assert "Followers" in body


async def test_profile_returns_404_for_unknown_account(monkeypatch):
    app = _app(monkeypatch, {"lookup": _resp(404, json={"detail": "x"})})

    response = await _fetch(app, "/@ghost")

    assert response.status_code == 404


async def test_profile_renders_without_posts_and_logs_when_statuses_fail(monkeypatch, caplog):
    app = _app(monkeypatch, {"lookup": _resp(200, json=_account()),
                             "statuses": _resp(500, text="boom")})

    with caplog.at_level(logging.WARNING):
        response = await _fetch(app, "/@alice")

    assert response.status_code == 200
    assert "No posts yet." in response.text
    assert any("statuses" in record.getMessage() and "500" in record.getMessage()
               for record in caplog.records)



def test_status_fragment_author_block_is_optional():
    status = {"content": "<p>x</p>",
              "created_at": "2026-01-01T00:00:00+00:00",
              "reblogs_count": 0,
              "favourites_count": 0,
              "account": {"display_name": "Bob",
                          "username": "bob",
                          "acct": "bob@remote.tld",
                          "url": "https://remote.tld/@bob",
                          "avatar": None}}

    template = _ENV.get_template("status.html")
 
    assert "Bob" in template.render(status=status)
    shown = template.render(status=status, show_author=True)
    assert "@bob@remote.tld" in shown and "https://remote.tld/@bob" in shown
    assert "Bob" not in template.render(status=status, show_author=False)


def test_masthead_nav_when_logged_in():
    out = _ENV.get_template("base.html").render(current_username="alice",
                                                login_url="/login?next=%2F%40alice")
    assert '<a href="/@alice">My profile</a>' in out
    assert "/settings" in out and "/logout" in out
    assert ">Login</a>" not in out and "/login?next=" not in out


def test_masthead_nav_when_logged_out():
    out = _ENV.get_template("base.html").render(current_username=None,
                                                login_url="/login?next=%2F%40bob")
    assert '<a href="/login?next=%2F%40bob">Login</a>' in out
    assert "My profile" not in out
    assert "/settings" not in out and "/logout" not in out


_ENV.filters["sanitize"] = templating.sanitize_html

async def test_profile_render_sanitizes_malicious_note(monkeypatch):
    account = _account()
    account["note"] = "<p>ok</p><script>alert(1)</script>"
    app = _app(monkeypatch, {"lookup": _resp(200, json=account),
                             "statuses": _resp(200, json=[])})
    response = await _fetch(app, "/@alice")
    assert "<p>ok</p>" in response.text
    assert "<script>" not in response.text

