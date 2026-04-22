# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import asyncpg
import uvicorn
from .app import create_app

from .s2s.webfinger import storage as webfinger_storage, projection as webfinger_projection
from .s2s.actor     import storage as actor_storage,     projection as actor_projection
from .s2s.inbox     import storage as inbox_storage,     projection as inbox_projection
from .s2s.outbox    import storage as outbox_storage,    projection as outbox_projection
from .c2s.oauth     import projection as oauth_projection
from .c2s.oauth     import router as oauth_router
from .c2s.timelines import storage as timelines_storage
from .c2s.timelines import projection as timelines_projection
from .c2s.instance  import router as instance_router
from .c2s.statuses  import router as statuses_router
from .c2s.accounts  import router as accounts_router
from .c2s.apps      import router as apps_router
from .c2s.timelines import router as timelines_router


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


async def _init_webfinger_router(config):
    await webfinger_storage.init(config)
    await (await webfinger_storage.storage()).ensure_table()
    await webfinger_projection.rebuild()

    _logged_task(webfinger_projection.handle_user_events(), "webfinger")


async def _init_actor_router(config):
    await actor_storage.init(config)
    await (await actor_storage.storage()).ensure_table()
    await actor_projection.rebuild()
     
    _logged_task(actor_projection.handle_user_events(), "actor")


async def _init_inbox_router(config):
    await inbox_storage.init(config)
    await (await inbox_storage.storage()).ensure_table()
    await inbox_projection.rebuild()
     
    _logged_task(inbox_projection.handle_user_events(), "inbox")


async def _init_outbox_router(config):
    await outbox_storage.init(config)
    await (await outbox_storage.storage()).ensure_table()
    await outbox_projection.rebuild()
     
    _logged_task(outbox_projection.handle_user_events(), "outbox")

 
async def _init_c2s_oauth_router(config):
    await oauth_projection.apps_rebuild()
    await oauth_projection.codes_rebuild()
    oauth_router.init(config)
    _logged_task(oauth_projection.apps_handle_events(), "c2s_oauth_apps")
    _logged_task(oauth_projection.codes_handle_events(), "c2s_oauth_codes")
 
 
async def _init_c2s_instance_router(config):
    instance_router.init(config)
 
 
async def _init_c2s_statuses_router(config):
    statuses_router.init(config)
 
 
async def _init_c2s_accounts_router(config):
    accounts_router.init(config)
 
 
async def _init_c2s_apps_router(config):
    apps_router.init(config)


async def _init_c2s_timelines_router(config):
    await timelines_storage.init(config)
    await (await timelines_storage.storage()).ensure_table()
    await timelines_projection.rebuild()
    timelines_router.init(config)
    _logged_task(timelines_projection.handle_events(), "c2s_timelines")


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
                    for name, ini in (("s2s_webfinger", _init_webfinger_router),
                                      ("s2s_actor",     _init_actor_router),
                                      ("s2s_inbox",     _init_inbox_router),
                                      ("s2s_outbox",    _init_outbox_router),

                                      ("c2s_oauth",     _init_c2s_oauth_router),
                                      ("c2s_instance",  _init_c2s_instance_router),
                                      ("c2s_statuses",  _init_c2s_statuses_router),
                                      ("c2s_accounts",  _init_c2s_accounts_router),
                                      ("c2s_apps",      _init_c2s_apps_router),
                                      ("c2s_timelines", _init_c2s_timelines_router))
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

