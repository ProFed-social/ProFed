# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
from typing import List
from collections.abc import Iterable
from fastapi import APIRouter
from profed.components.api.http import MastodonJSONResponse
from profed.core.media_storage import init_media_storage
from profed.components.api.active_routers import get_active

from profed.components.api.c2s.shared.actors import storage as actors_storage
from profed.components.api.c2s.shared.actors import projection as actors_projection

from .media import router as media
from .apps import router as apps
from .instance import router as instance
from .accounts import router as accounts
from .statuses import router as statuses
from profed.components.api.c2s.shared.statuses import as_objects as statuses_objects
from profed.components.api.c2s.shared.statuses import user_timeline as statuses_memberships
from profed.components.api.c2s.shared.statuses import projection as statuses_projection
from profed.components.api.c2s.shared.statuses import compressor as statuses_compressor
from .timelines import router as timelines
from .notifications import router as notifications
from .lists import router as lists
from .markers import router as markers
from .accounts.follows import storage as follows_storage
from .accounts.follows import projection as follows_projection
from .accounts.preferences import storage as preferences_storage
from .accounts.preferences import projection as preferences_projection
from .accounts.statuses import storage as user_statuses_storage
from .accounts.statuses import projection as user_statuses_projection


def _projection_initializer(storages, projection, handle_events, name):
    async def _init_projection(config: dict):
        for storage in storages if isinstance(storages, Iterable) else [storages]:
            await storage.init(config)
            await (await storage.storage()).ensure_schema()
        await projection.rebuild()
        asyncio.create_task(handle_events(), name=name)

    return _init_projection


def _compressor_initializer(compressor):
    async def _init(config: dict):
        compressor.start(config.get("compression", {}))
    return _init


async def init(config: dict, deactivate: List[str]) -> None:
    if any(router not in deactivate for router in ("accounts", "statuses")):
        await init_media_storage()

    for routers, init_fn in [(["accounts"],
                              _projection_initializer(actors_storage,
                                                      actors_projection,
                                                      actors_projection.handle_account_events,
                                                      "c2s_actor")),
                             (["timelines", "statuses", "accounts"],
                              _projection_initializer([statuses_objects, statuses_memberships],
                                                      statuses_projection,
                                                      statuses_projection.handle_events,
                                                      "c2s_statuses")),
                             (["timelines", "statuses", "accounts"], _compressor_initializer(statuses_compressor)),
                             (["accounts"],
                              _projection_initializer(follows_storage,
                                                      follows_projection,
                                                      follows_projection.handle_events,
                                                      "c2s_v1_follows")),
                             (["accounts"],
                              _projection_initializer(preferences_storage,
                                                      preferences_projection,
                                                      preferences_projection.handle_events,
                                                      "c2s_v1_preferences")),
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
    router = APIRouter(prefix="/v1", default_response_class=MastodonJSONResponse)
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

