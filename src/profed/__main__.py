# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import asyncio

from functools import partial

import uvicorn
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

from profed.core.config import config
from profed.core.component_manager import run, collect_component_hooks
from profed.core.message_bus import init_message_bus
from profed.topics import names


STANDARD_COMPONENTS = ["api",
                       "client",
                       "user_activities",
                       "activity_delivery",
                       "follow_handler",
                       "accept_handler"]


class _ProxyAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, proxy_token: str):
        super().__init__(app)
        self._proxy_token = proxy_token

    async def dispatch(self, request, call_next):
        if request.headers.get("x-forwarded-proto") != "https":
            return StarletteResponse(status_code=400, content="HTTPS required")

        if (self._proxy_token not in ("", request.headers.get("x-internal-token"))):
            return StarletteResponse(status_code=403, content="Missing or invalid proxy token")

        return await call_next(request)


async def web_service():
    cfg = config()

    mounts = collect_component_hooks(cfg["profed"]["run"], "mount_endpoints")
    if not mounts:
        return

    web = cfg.get("web-server", {})
    if "proxy_token" not in web:
        raise RuntimeError('proxy_token is required in [web-server] config. '
                           'Set to empty string ("") to disable the token check.')

    app = FastAPI()
    app.add_middleware(_ProxyAuthMiddleware, proxy_token=web["proxy_token"])

    await asyncio.gather(*(hook(app, cfg.get(name, {}))
                           for name, hook in mounts.items()))

    server = uvicorn.Server(uvicorn.Config(app,
                                           host=web.get("listen_host", "127.0.0.1"),
                                           port=int(web.get("listen_port", 8000)),
                                           loop="asyncio"))
    await server.serve()


if __name__ == "__main__":
    config.set_defaults({"profed": {"run": STANDARD_COMPONENTS}})
    cfg = config()

    logging.basicConfig(level=logging.WARNING,
                        format="%(levelname)s %(name)s %(message)s")
    level = cfg.get("logging", {}).get("level", "INFO")
    logging.getLogger().setLevel(getattr(logging, level.upper()))

    run(cfg,
        init=[partial(init_message_bus, names())],
        services=[web_service])

