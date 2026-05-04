# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from fastapi import FastAPI
from .active_routers import narrow_deactivate_routers
from . import s2s, c2s
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse


class _ProxyAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self,
                 app,
                 proxy_token: str):
        super().__init__(app)
        self._proxy_token = proxy_token

    async def dispatch(self, request, call_next):
        if request.headers.get("x-forwarded-proto") != "https":
            return StarletteResponse(status_code=400,
                                         content="HTTPS required")

        if self._proxy_token != "":
            if request.headers.get("x-internal-token") != self._proxy_token:
                return StarletteResponse(status_code=403,
                                             content="Missing or invalid proxy token")

        return await call_next(request)


def create_app(config):
    app = FastAPI()

    app.add_middleware(_ProxyAuthMiddleware,
                       proxy_token=config["proxy_token"])

    deactivate_routers = config.get("deactivate_routers", "").split()
    for name, mount in {"s2s": s2s.mount_routers,
                        "c2s": c2s.mount_routers}.items():
        if name not in deactivate_routers:
            mount(app, narrow_deactivate_routers(f"{name}_", deactivate_routers))

    return app

