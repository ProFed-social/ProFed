# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import asyncio
from typing import List
from fastapi import APIRouter
from profed.components.api.active_routers import get_active
from .apps      import router as apps
from .instance  import router as instance
from .accounts  import router as accounts
from .statuses  import router as statuses
from .timelines import storage as timelines_storage
from .timelines import projection as timelines_projection
from .timelines import router as timelines
from profed.components.api.c2s.shared.actors import storage as actors_storage
from profed.components.api.c2s.shared.actors import projection as actors_projection
from .accounts.following import storage as following_storage
from .accounts.following import projection as following_projection 

def _projection_initializer(storage, projection, handle_events, name):
    async def _init_projection(config: dict):
        await storage.init(config)
        await (await storage.storage()).ensure_table()
        await projection.rebuild()
        asyncio.create_task(handle_events(), name=name)

    return _init_projection

 
async def init(config: dict, deactivate: List[str]) -> None:
    for routers, init in [(["accounts"],
                           _projection_initializer(actors_storage,
                                                   actors_projection,
                                                   actors_projection.handle_user_events,
                                                   "c2s_actor")),
                          (["timelines"],
                           _projection_initializer(timelines_storage,
                                                   timelines_projection,
                                                   timelines_projection.handle_events,
                                                   "c2s_v1_timelines")),
                          (["accounts"],
                           _projection_initializer(following_storage,
                                                   following_projection,
                                                   following_projection.handle_events,
                                                   "c2s_v1_following"))]:
        if any(r not in deactivate for r in routers):
            await init(config)

    for r in get_active({"apps": apps,
                         "instance": instance,
                         "accounts": accounts,
                         "statuses": statuses,
                         "timelines": timelines},
                        deactivate):
        r.init(config)


def mount_routers(parent, deactivate: List[str]) -> None:
    router = APIRouter(prefix="/v1")
    for r in get_active({"apps":      apps,
                         "instance":  instance,
                         "accounts":  accounts,
                         "statuses":  statuses,
                         "timelines": timelines},
                        deactivate):
        if r.active:
            router.include_router(r.router)
    parent.include_router(router)

