# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
from typing import List
from fastapi import APIRouter
from profed.core.media_storage import init_media_storage
from profed.components.api.active_routers import get_active

from profed.components.api.c2s.shared.actors import storage as actors_storage
from profed.components.api.c2s.shared.actors import projection as actors_projection

from .media         import router as media
from .accounts.following import storage as following_storage
from .apps      import router as apps
from .instance  import router as instance
from .accounts  import router as accounts
from .statuses  import router as statuses
from .timelines import storage as timelines_storage
from .timelines import projection as timelines_projection
from .timelines import router as timelines
from .notifications import router as notifications
from .lists         import router as lists
from .markers       import router as markers
from .media         import router as media
from .accounts.following import storage as following_storage
from .accounts.following import projection as following_projection 
from .accounts.followers import storage   as followers_storage
from .accounts.followers import projection as followers_projection
from .accounts.follows import storage as follows_storage
from .accounts.follows import projection as follows_projection
from .accounts.statuses import storage as user_statuses_storage
from .accounts.statuses import projection as user_statuses_projection


def _projection_initializer(storage, projection, handle_events, name):
    async def _init_projection(config: dict):
        await storage.init(config)
        await (await storage.storage()).ensure_schema()
        await projection.rebuild()
        asyncio.create_task(handle_events(), name=name)

    return _init_projection

 
async def init(config: dict, deactivate: List[str]) -> None:
    if any(router not in deactivate for router in ("accounts", "statuses")):
        await init_media_storage()

    for routers, init_fn in [(["accounts"],
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
                                                      "c2s_v1_following")),
                             (["accounts"],
                              _projection_initializer(followers_storage,
                                                      followers_projection,
                                                      followers_projection.handle_events,
                                                      "c2s_v1_followers")),
                             (["accounts"],
                              _projection_initializer(follows_storage,
                                                      follows_projection,
                                                      follows_projection.handle_events,
                                                      "c2s_v1_follows")),
                             (["accounts"],
                               _projection_initializer(user_statuses_storage,
                                                      user_statuses_projection,
                                                      user_statuses_projection.handle_events,
                                                      "c2s_v1_user_statuses"))]:
        if any(r not in deactivate for r in routers):
            await init_fn(config)

    for r in get_active({"apps": apps,
                         "instance": instance,
                         "accounts": accounts,
                         "statuses": statuses,
                         "timelines": timelines,
                         "notifications": notifications,
                         "lists": lists,
                         "markers": markers,
                         "media": media},
                        deactivate):
        r.init(config)


def mount_routers(parent, deactivate: List[str]) -> None:
    router = APIRouter(prefix="/v1")
    for r in get_active({"apps": apps,
                         "instance": instance,
                         "accounts": accounts,
                         "statuses": statuses,
                         "timelines": timelines,
                         "notifications": notifications,
                         "lists": lists,
                         "markers": markers,
                         "media": media},
                        deactivate):
        router.include_router(r.router)
    parent.include_router(router)

