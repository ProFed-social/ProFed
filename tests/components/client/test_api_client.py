# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from fastapi import FastAPI
from pytest import raises

from profed.__main__ import _ProxyAuthMiddleware
from profed.components.client import api_client as mod
from profed.components.client.api_client import ApiClient


def _local_app():
    app = FastAPI()

    @app.get("/api/v1/ping")
    async def ping():
        return {"ok": True}

    @app.get("/items/{item_id}")
    async def item(item_id: str):
        return {"id": item_id}

    return app


def test_is_local_matches_mounted_paths():
    client = ApiClient(_local_app(), "https://example.test", "", False)
    assert client._is_local("GET", "/api/v1/ping")
    assert client._is_local("GET", "/items/42")
    assert not client._is_local("GET", "/nope")


def test_select_picks_local_external_and_honours_force():
    client = ApiClient(_local_app(), "https://example.test", "", False)
    assert client._select("GET", "/api/v1/ping") is client._local
    assert client._select("GET", "/nope") is client._external

    forced = ApiClient(_local_app(), "https://example.test", "", True)
    assert forced._select("GET", "/api/v1/ping") is forced._external


def test_proxy_headers_only_on_the_local_transport():
    client = ApiClient(_local_app(), "https://example.test", "secret", False)
    assert client._local.headers["x-forwarded-proto"] == "https"
    assert client._local.headers["x-internal-token"] == "secret"
    assert "x-forwarded-proto" not in client._external.headers
    assert "x-internal-token" not in client._external.headers


async def test_in_process_call_passes_the_proxy_middleware():
    app = FastAPI()
    app.add_middleware(_ProxyAuthMiddleware, proxy_token="secret")

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    client = ApiClient(app, "https://example.test", "secret", False)
    response = await client.get("/ping")

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_api_client_requires_bind():
    mod._reset_api_client()
    with raises(RuntimeError):
        mod.api_client()


def test_api_client_is_built_after_bind_and_resettable(monkeypatch):
    monkeypatch.setattr(mod, "config", lambda: {})
    monkeypatch.setattr(mod, "domain", lambda: "example.test")
    mod._reset_api_client()

    mod.bind(_local_app())
    first = mod.api_client()
    assert isinstance(first, ApiClient)
    assert mod.api_client() is first

    mod._reset_api_client()
    with raises(RuntimeError):
        mod.api_client()

