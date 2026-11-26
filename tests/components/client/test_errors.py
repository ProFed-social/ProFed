# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from starlette.testclient import TestClient

from profed.components.client import auth, errors, templating
from profed.components.client.errors import ClientError
from profed.components.client.templating import STANDARD_TEMPLATES, build_environment


CLIENT_CFG = {"client": {"client_id": "cid",
                         "client_secret": "csecret",
                         "scope": "read write",
                         "session_ttl": 86400,
                         "cookie_secure": True}}


@pytest.fixture(autouse=True)
def templates():
    templating._instance = build_environment(STANDARD_TEMPLATES, None)
    yield
    templating._reset_environment()


def _app():
    app = FastAPI()
    errors.mount(app)
    app.include_router(auth.router)

    @app.get("/breaks")
    async def breaks():
        raise ClientError(418, "A short title", "A longer explanation.", "/elsewhere")

    @app.get("/breaks-without-retry")
    async def breaks_without_retry():
        raise ClientError(503, "No retry here", "Nothing to try again.")

    @app.get("/api/breaks")
    async def api_breaks():
        raise HTTPException(status_code=418, detail="stays_json")

    return app


def _response(status=200, text=""):
    response = MagicMock()
    response.status_code = status
    response.text = text
    response.json = MagicMock(return_value={})

    return response


def test_a_client_error_becomes_a_readable_page():
    response = TestClient(_app(), raise_server_exceptions=False).get("/breaks")

    assert response.status_code == 418
    assert response.headers["content-type"].startswith("text/html")
    assert "A short title" in response.text
    assert "A longer explanation." in response.text
    assert 'href="/elsewhere"' in response.text


def test_a_client_error_without_a_retry_offers_no_link():
    response = TestClient(_app(), raise_server_exceptions=False).get("/breaks-without-retry")

    assert response.status_code == 503
    assert "Nothing to try again." in response.text
    assert "Try again" not in response.text


def test_the_page_carries_no_detail_json():
    response = TestClient(_app(), raise_server_exceptions=False).get("/breaks")

    assert '"detail"' not in response.text


def test_an_http_exception_still_answers_with_json():
    response = TestClient(_app(), raise_server_exceptions=False).get("/api/breaks")

    assert response.json() == {"detail": "stays_json"}


def test_a_sign_in_link_from_another_session_explains_itself():
    client = TestClient(_app(), raise_server_exceptions=False)
    client.cookies.set("oauth_state", "other")

    with patch("profed.components.client.auth.config", new=lambda: CLIENT_CFG):
        response = client.get("/auth/callback?code=c&state=s", follow_redirects=False)

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("text/html")
    assert "Sign-in failed" in response.text
    assert "cookies are blocked" in response.text


def test_a_failed_token_exchange_explains_itself():
    api = MagicMock()
    api.post = AsyncMock(return_value=_response(400, '{"detail":"invalid_grant"}'))
    client = TestClient(_app(), raise_server_exceptions=False)
    client.cookies.set("oauth_state", "s")

    with patch("profed.components.client.auth.config", new=lambda: CLIENT_CFG), \
         patch("profed.components.client.auth.api_client", return_value=api):
        response = client.get("/auth/callback?code=the-code&state=s", follow_redirects=False)

    assert response.status_code == 502
    assert response.headers["content-type"].startswith("text/html")
    assert "Sign-in failed" in response.text
    assert "signing in again usually works" in response.text
    assert 'href="/login"' in response.text

