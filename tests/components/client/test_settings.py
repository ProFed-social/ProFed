# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import httpx
from fastapi import FastAPI
from jinja2 import Environment, select_autoescape

from profed.components.client import settings, templating, auth


_ENV = Environment(loader=templating.build_loader(templating.STANDARD_TEMPLATES, None),
                   autoescape=select_autoescape(["html", "xml"]))


def _resp(status_code, **kwargs):
    return httpx.Response(status_code,
                          request=httpx.Request("GET", "https://test.local/api"),
                          **kwargs)


class _FakeClient:
    def __init__(self, responses):
        self._responses = responses
        self.calls = []

    async def get(self, path, **kwargs):
        return self._match(path, kwargs)

    async def patch(self, path, **kwargs):
        return self._match(path, kwargs)

    def _match(self, path, kwargs):
        self.calls.append((path, kwargs))
        for marker, response in self._responses.items():
            if marker in path:
                return response

        return _resp(404)


def _session(value):
    async def _user(request):
        return value

    return _user


def _app(monkeypatch, responses, session):
    client = _FakeClient(responses)
    monkeypatch.setattr(settings, "api_client", lambda: client)
    monkeypatch.setattr(settings, "environment", lambda: _ENV)
    monkeypatch.setattr(auth, "current_user_optional", _session(session))

    app = FastAPI()
    app.include_router(settings.router)

    return app, client


def _preferences():
    return {"posting:default:visibility": "unlisted",
            "posting:default:sensitive": False,
            "posting:default:language": "de"}


def _credential_account(privacy="private", sensitive=True, language="en"):
    return {"source": {"privacy": privacy, "sensitive": sensitive, "language": language}}


def _instance():
    return _resp(200, json={"languages": ["de", "en", "fr"]})


async def _fetch(app, method, path, **kwargs):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://test.local") as client:
        return await client.request(method, path, **kwargs)


async def test_settings_redirects_to_login_without_session(monkeypatch):
    app, _ = _app(monkeypatch, {}, None)

    response = await _fetch(app, "GET", "/settings")

    assert response.status_code == 303
    assert response.headers["location"] == "/login?next=%2Fsettings"

async def test_settings_renders_form_with_current_preferences(monkeypatch):
    app, client = _app(monkeypatch,
                       {"preferences": _resp(200, json=_preferences()),
                        "instance": _instance()},
                       {"username": "alice", "token": "tok"})

    response = await _fetch(app, "GET", "/settings")

    assert response.status_code == 200
    body = response.text
    assert 'name="visibility"' in body
    assert '<option value="unlisted" selected' in body
    assert 'name="language"' in body and '<option value="de" selected' in body
    assert client.calls[0][1]["token"] == "tok"
    assert "/logout" in body


async def test_update_settings_patches_credentials_and_marks_saved(monkeypatch):
    app, client = _app(monkeypatch,
                       {"update_credentials": _resp(200, json=_credential_account(privacy="public",
                                                                                  sensitive=False,
                                                                                  language="fr")),
                        "instance": _instance()},
                       {"username": "alice", "token": "tok"})

    response = await _fetch(app, "POST", "/settings",
                            data={"visibility": "public", "language": "fr"})

    assert response.status_code == 200
    body = response.text
    assert "Settings saved." in body
    assert '<option value="public" selected' in body
    assert '<option value="fr" selected' in body

    payload = client.calls[0][1]["data"]
    assert payload["source[privacy]"] == "public"
    assert payload["source[sensitive]"] == "false"
    assert payload["source[language]"] == "fr"


async def test_update_settings_sends_sensitive_true_when_checked(monkeypatch):
    app, client = _app(monkeypatch,
                       {"update_credentials": _resp(200, json=_credential_account()),
                        "instance": _instance()},
                       {"username": "alice", "token": "tok"})

    await _fetch(app, "POST", "/settings",
                 data={"visibility": "private", "sensitive": "on", "language": "en"})

    assert client.calls[0][1]["data"]["source[sensitive]"] == "true"


async def test_update_settings_reports_validation_error(monkeypatch):
    app, _ = _app(monkeypatch,
                  {"update_credentials": _resp(422, json={"error": "bad language"}),
                   "instance": _instance()},
                  {"username": "alice", "token": "tok"})

    response = await _fetch(app, "POST", "/settings",
                            data={"visibility": "public", "language": "de"})

    assert response.status_code == 422
    body = response.text
    assert "Could not save settings." in body
    assert '<option value="public" selected' in body
    assert '<option value="de" selected' in body


async def test_update_settings_redirects_via_htmx_without_session(monkeypatch):
    app, _ = _app(monkeypatch, {}, None)

    response = await _fetch(app, "POST", "/settings", data={"visibility": "public"})

    assert response.status_code == 401
    assert response.headers["HX-Redirect"] == "/login?next=%2Fsettings"


