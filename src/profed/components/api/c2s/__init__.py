# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later


import asyncio
from typing import List
from profed.components.api.active_routers import narrow_deactivate_routers
from profed.components.api.c2s.shared.known_accounts import storage as known_accounts_storage
from profed.components.api.c2s.shared.known_accounts import projection as known_accounts_projection
from . import oauth
from . import v1, v2
from .router import mount_routers


def _projection_initializer(storage, projection, handle_events, name):
    async def _init(config: dict):
        await storage.init(config)
        await (await storage.storage()).ensure_table()
        await projection.rebuild()
        asyncio.create_task(handle_events(), name=name)
    return _init


async def init(config: dict, deactivate: List[str]) -> None:
    v1_deactivate = narrow_deactivate_routers("v1_", deactivate)
    v2_deactivate = narrow_deactivate_routers("v2_", deactivate)
    for routers, init_fn in [(["v1_search", "v1_accounts", "v2_search"],
                               _projection_initializer(known_accounts_storage,
                                                       known_accounts_projection,
                                                       known_accounts_projection.handle_events,
                                                       "c2s_known_accounts"))]:
        if any(r not in deactivate for r in routers):
            await init_fn(config)
    if "oauth" not in deactivate:
        await oauth.init(config)
    await v1.init(config, v1_deactivate)
    await v2.init(config, v2_deactivate)

