# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import uvicorn

from .app import create_app

from .active_routers import narrow_deactivate_routers
from . import s2s, c2s


using_schemata = ["api"]


async def Api(config):
    if "proxy_token" not in config:
        raise RuntimeError(
            "proxy_token is required in [api] config. "
            'Set to empty string ("") to disable the token check.')

    deactivate = config.get("deactivate_routers", "").split()

    for name, init in {"s2s": s2s.init, "c2s": c2s.init}.items():
        if name not in deactivate:
            await init(config, narrow_deactivate_routers(f"{name}_", deactivate))

    app = create_app(config)

    server = uvicorn.Server(uvicorn.Config(app,
                                           host=config.get("listen_host", "127.0.0.1"),
                                           port=int(config.get("listen_port", 8000)),
                                           loop="asyncio"))
    await server.serve()

