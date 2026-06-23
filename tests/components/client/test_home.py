# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import AsyncMock

import httpx
from fastapi import FastAPI
from jinja2 import Environment, select_autoescape

from profed.components.client import auth, home, templating


_ENV = Environment(loader=templating.build_loader(templating.STANDARD_TEMPLATES, None),
                   autoescape=select_autoescape(["html", "xml"]))


def _app(monkeypatch):
    monkeypatch.setattr(home, "environment", lambda: _ENV)

    app = FastAPI()
    app.include_router(home.router)

    return app


async def _fetch(app, path):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://test.local") as client:
        return await client.get(path)


async def test_home_renders_masthead_for_anonymous_visitor(monkeypatch):
    response = await _fetch(_app(monkeypatch), "/")

    assert response.status_code == 200
    body = response.text
    assert "ProFed" in body
    assert "/login?next=" in body
    assert "/settings" not in body and "/logout" not in body


async def test_home_renders_logged_in_nav(monkeypatch):
    monkeypatch.setattr(auth, "current_user_optional",
                        AsyncMock(return_value={"username": "christof", "token": "t"}))

    response = await _fetch(_app(monkeypatch), "/")

    assert response.status_code == 200
    body = response.text
    assert "/@christof" in body and "/settings" in body and "/logout" in body
    assert ">Login</a>" not in body

