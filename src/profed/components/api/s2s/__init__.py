# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later


import asyncio
from typing import List
from profed.components.api.active_routers import get_active
from .webfinger import storage as webfinger_storage, projection as webfinger_projection
from .actor     import storage as actor_storage,     projection as actor_projection
from .inbox     import storage as inbox_storage,     projection as inbox_projection
from .inbox     import public_keys_storage as inbox_public_keys_storage, \
                       public_keys_projection as inbox_public_keys_projection
from .outbox    import storage as outbox_storage,    projection as outbox_projection
from .webfinger import router as webfinger_router
from .actor     import router as actor_router
from .inbox     import router as inbox_router
from .outbox    import router as outbox_router
from .nodeinfo  import router as nodeinfo_router 
 
async def init(config: dict, deactivate: List[str]) -> None:
    for storage, projection, task_name in get_active({"webfinger": (webfinger_storage,
                                                                    webfinger_projection,
                                                                    "s2s_webfinger"),
                                                      "actor": (actor_storage,
                                                                actor_projection,
                                                                "s2s_actor"),
                                                      "inbox": (inbox_storage,
                                                                inbox_projection,
                                                                "s2s_inbox"),
                                                      "inbox_public_keys": (inbox_public_keys_storage,
                                                                            inbox_public_keys_projection,
                                                                            "s2s_inbox_public_keys"),
                                                      "outbox": (outbox_storage,
                                                                 outbox_projection,
                                                                 "s2s_outbox")},
                                                     deactivate):
        await storage.init(config)
        await (await storage.storage()).ensure_schema()
        await projection.rebuild()
        asyncio.create_task(projection.handle_user_events(), name=task_name)
 
 
def mount_routers(parent, deactivate: List[str]) -> None:
    for r in get_active({"webfinger": webfinger_router,
                         "actor":     actor_router,
                         "inbox":     inbox_router,
                         "outbox":    outbox_router,
                         "nodeinfo":  nodeinfo_router},
                        deactivate):
        parent.include_router(r.router)

