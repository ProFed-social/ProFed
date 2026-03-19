# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from threading import Thread
import asyncio
import asyncpg
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


async def _init_well_known_router(component_name: str, config):
    await webfinger_storage.init(component_name, config)
    await (await webfinger_storage.storage()).ensure_table()
    await webfinger_projections.rebuild()

    asyncio.create_task(webfinger_projections.handle_user_events())


async def _init_actor_router(component_name: str, config):
    await actor_storage.init(component_name, config)
    await (await actor_storage.storage()).ensure_table()
    await actor_projections.rebuild()
     
    asyncio.create_task(actor_projections.handle_user_events())


async def _init_inbox_router(component_name: str, config):
    await inbox_storage.init(component_name, config)
    await (await inbox_storage.storage()).ensure_table()
    await inbox_projections.rebuild()
     
    asyncio.create_task(inbox_projections.handle_user_events())


async def _init_outbox_router(component_name: str, config):
    await outbox_storage.init(component_name, config)
    await (await outbox_storage.storage()).ensure_table()
    await outbox_projections.rebuild()
     
    asyncio.create_task(outbox_projections.handle_user_events())


async def _reset_component_schema(component_name: str, config):
    pool = await asyncpg.create_pool(host=config["host"],
                                     port=int(config["port"]),
                                     database=config["database"],
                                     user=config["user"],
                                     password=config["password"],)
    async with pool.acquire() as conn:
        await conn.execute(f"DROP SCHEMA IF EXISTS {component_name} CASCADE")
        await conn.execute(f"CREATE SCHEMA {component_name}")


async def init(component_name: str, config):
    await _reset_component_schema(component_name, config)

    deactive_routers = config.get("deactive_routers", "").split()
    init_routers = [ini
                    for name, ini in (("well_known", _init_well_known_router),
                                      ("actor", _init_actor_router),
                                       ("inbox", _init_inbox_router),
                                       ("outbox", _init_outbox_router),
                                       )
                    if name not in deactive_routers]
    
    for ini in init_routers:
        print(f"call router init function: {ini}")
        await ini(component_name, config)

    app = create_app(config)
    return app
