# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import httpx
from starlette.routing import Match

from profed.core.config import config
from profed.identity import domain


_app = None
_instance = None


class ApiClient:
    def __init__(self, app, base_url, proxy_token, force_external):
        self._app = app
        self._force_external = force_external
        self._routes = None

        self._local = httpx.AsyncClient(base_url=base_url,
                                        transport=httpx.ASGITransport(app=app),
                                        headers={"x-forwarded-proto": "https",
                                                 "x-internal-token": proxy_token})
        self._external = httpx.AsyncClient(base_url=base_url)

    def _is_local(self, method, path):
        if self._routes is None:
            self._routes = list(self._app.routes)

        scope = {"type": "http", "method": method, "path": path}
        return any(route.matches(scope)[0] == Match.FULL for route in self._routes)

    def _select(self, method, path):
        return (self._external
                if self._force_external or not self._is_local(method, path) else
                self._local)

    async def request(self, method, path, **kwargs):
        return await self._select(method, path).request(method, path, **kwargs)

    async def get(self, path, **kwargs):
        return await self.request("GET", path, **kwargs)


def bind(app):
    global _app
    _app = app


def api_client():
    global _instance
    if _instance is None:
        if _app is None:
            raise RuntimeError("client.api_client: bind(app) must run first")

        _instance = ApiClient(_app,
                              f"https://{domain()}",
                              config().get("web-server", {}).get("proxy_token", ""),
                              _as_bool(config().get("client", {}).get("force_external")))

    return _instance


def _as_bool(value):
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _reset_api_client():
    global _app, _instance
    _app = None
    _instance = None
