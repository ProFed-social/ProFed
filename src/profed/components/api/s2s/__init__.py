# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later


import asyncio
from typing import List
from profed.core.media_storage import init_media_storage
from profed.components.api.active_routers import get_active

from .webfinger import projection as webfinger_projection
from .actor import projection as actor_projection
from .inbox import projection as inbox_projection
from .inbox import public_keys_projection as inbox_public_keys_projection
from .outbox import projection as outbox_projection
from .instance_actor import projection as instance_actor_projection

from .webfinger import router as webfinger_router
from .actor import router as actor_router
from .inbox import router as inbox_router
from .outbox import router as outbox_router
from .nodeinfo import router as nodeinfo_router
from .outbox import reactions_projection, signers_projection, followers_projection
from .instance_actor import router as instance_actor_router


def _projection_initializer(projection, handle_events, name):
    async def _init(config: dict):
        await projection.init(config)
        await projection.rebuild()
        asyncio.create_task(handle_events(), name=name)
    return _init


async def init(config: dict, deactivate: List[str]) -> None:
    if "actor" not in deactivate:
        await init_media_storage()
    for routers, init_fn in [(["webfinger"],
                              _projection_initializer(webfinger_projection,
                                                      webfinger_projection.handle_user_events,
                                                      "s2s_webfinger")),
                             (["actor"],
                              _projection_initializer(actor_projection,
                                                      actor_projection.handle_user_events,
                                                      "s2s_actor")),
                             (["inbox"],
                              _projection_initializer(inbox_projection,
                                                      inbox_projection.handle_user_events,
                                                      "s2s_inbox")),
                             (["inbox_public_keys"],
                              _projection_initializer(inbox_public_keys_projection,
                                                      inbox_public_keys_projection.handle_user_events,
                                                      "s2s_inbox_public_keys")),
                             (["outbox"],
                              _projection_initializer(reactions_projection,
                                                      reactions_projection.handle_events,
                                                      "s2s_reactions")),
                             (["outbox"],
                              _projection_initializer(signers_projection,
                                                      signers_projection.handle_user_events,
                                                      "s2s_outbox_signers")),
                             (["outbox"],
                              _projection_initializer(followers_projection,
                                                      followers_projection.handle_user_events,
                                                      "s2s_outbox_followers")),
                             (["outbox"],
                              _projection_initializer(outbox_projection,
                                                      outbox_projection.handle_user_events,
                                                      "s2s_outbox")),
                             (["instance_actor", "inbox"],
                              _projection_initializer(instance_actor_projection,
                                                      instance_actor_projection.handle_user_events,
                                                      "s2s_instance_actor"))]:
        if any(r not in deactivate for r in routers):
            await init_fn(config)


def mount_routers(parent, deactivate: List[str]) -> None:
    for r in get_active({"webfinger": webfinger_router,
                         "actor": actor_router,
                         "inbox": inbox_router,
                         "outbox": outbox_router,
                         "nodeinfo": nodeinfo_router,
                         "instance_actor": instance_actor_router},
                        deactivate):
        parent.include_router(r.router)

