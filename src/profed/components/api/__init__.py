# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import asyncpg
import uvicorn
from .app import create_app
from .storage import (
        webfinger_users as webfinger_storage,
        actor as actor_storage,
        inbox_users as inbox_storage,
        outbox as outbox_storage)
from .projections import (
        webfinger as webfinger_projections,
        actor as actor_projections,
        inbox as inbox_projections,
        outbox as outbox_projections)
import logging


logger = logging.getLogger(__name__)

def _logged_task(coro, name):
    async def _wrapper():
        try:
            await coro
        except Exception:
            logger.exception("Projection task %s failed", name)
            raise
    return asyncio.create_task(_wrapper(), name=name)


async def _init_well_known_router(config):
    await webfinger_storage.init(config)
    await (await webfinger_storage.storage()).ensure_table()
    await webfinger_projections.rebuild()

    _logged_task(webfinger_projections.handle_user_events(), "webfinger")


async def _init_actor_router(config):
    await actor_storage.init(config)
    await (await actor_storage.storage()).ensure_table()
    await actor_projections.rebuild()
     
    _logged_task(actor_projections.handle_user_events(), "actor")


async def _init_inbox_router(config):
    await inbox_storage.init(config)
    await (await inbox_storage.storage()).ensure_table()
    await inbox_projections.rebuild()
     
    _logged_task(inbox_projections.handle_user_events(), "inbox")


async def _init_outbox_router(config):
    await outbox_storage.init(config)
    await (await outbox_storage.storage()).ensure_table()
    await outbox_projections.rebuild()
     
    _logged_task(outbox_projections.handle_user_events(), "outbox")


async def _reset_component_schema(config):
    pool = await asyncpg.create_pool(host=config["host"],
                                     port=int(config["port"]),
                                     database=config["database"],
                                     user=config["user"],
                                     password=config["password"],)
    async with pool.acquire() as conn:
        await conn.execute(f"DROP SCHEMA IF EXISTS api CASCADE")
        await conn.execute(f"CREATE SCHEMA api")


async def Api(config):
    await _reset_component_schema(config)

    deactivate_routers = config.get("deactivate_routers", "").split()
    init_routers = [ini
                    for name, ini in (("s2s_well_known", _init_well_known_router),
                                      ("s2s_actor", _init_actor_router),
                                      ("s2s_inbox", _init_inbox_router),
                                      ("s2s_outbox", _init_outbox_router))
                    if name not in deactivate_routers]
    
    for ini in init_routers:
        print(f"call router init function: {ini}")
        await ini(config)

    app = create_app(config)

    server = uvicorn.Server(uvicorn.Config(app,
                                           host=config.get("listen_host", "127.0.0.1"),
                                           port=int(config.get("listen_port", 8000)),
                                           loop="asyncio"))
    await server.serve()

