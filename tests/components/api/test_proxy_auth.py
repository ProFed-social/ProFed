# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from profed.components.api.app import _ProxyAuthMiddleware


def _make_client(proxy_token: str) -> TestClient:
    app = FastAPI()
    app.add_middleware(_ProxyAuthMiddleware,
                       proxy_token=proxy_token)
    @app.get("/test")
    async def test_endpoint():
        return {"ok": True}
    return TestClient(app, raise_server_exceptions=False)


def test_missing_forwarded_proto_is_rejected():
    client = _make_client("")
    response = client.get("/test")

    assert response.status_code == 400


def test_http_forwarded_proto_is_rejected():
    client = _make_client("")
    response = client.get("/test", headers={"x-forwarded-proto": "http"})

    assert response.status_code == 400


def test_https_forwarded_proto_without_token_config_is_accepted():
    client = _make_client("")
    response = client.get("/test", headers={"x-forwarded-proto": "https"})

    assert response.status_code == 200


def test_missing_internal_token_is_rejected():
    client = _make_client("secret")
    response = client.get("/test", headers={"x-forwarded-proto": "https"})

    assert response.status_code == 403


def test_wrong_internal_token_is_rejected():
    client = _make_client("secret")
    response = client.get("/test",
                           headers={"x-forwarded-proto":  "https",
                                    "x-internal-token":   "wrong"})

    assert response.status_code == 403


def test_correct_internal_token_is_accepted():
    client = _make_client("secret")
    response = client.get("/test",
                           headers={"x-forwarded-proto": "https",
                                    "x-internal-token":  "secret"})

    assert response.status_code == 200


def test_missing_proxy_token_config_raises_on_startup():
    from unittest.mock import AsyncMock, patch
    import asyncio
    from profed.components.api import Api
    async def _run():
        with patch("profed.components.api._reset_component_schema",
                   AsyncMock()):
            await Api({})
    with pytest.raises(RuntimeError, match="proxy_token"):
        asyncio.get_event_loop().run_until_complete(_run())

