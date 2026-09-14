# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.message_bus import message_bus
from profed.identity import is_local_actor_url
from profed.topics.known_servers_topic import host_of
from profed.topics.unknown_actors_topic import throttled_id
from .storage import storage


async def _discover(host: str) -> None:
    async with message_bus().topic("known_servers").publish() as publish:
        await publish(event_type="discovered",
                      object_id=host,
                      payload={},
                      message_id=throttled_id("known_servers", host))


async def understands_reactions(actor_url: str) -> bool:
    if is_local_actor_url(actor_url):
        return True

    host = host_of(actor_url)
    supported = None if not host else await (await storage()).support_of(host)
    if supported is None and host:
        await _discover(host)

    return bool(supported)

