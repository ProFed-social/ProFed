# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.projections import build_projection, with_emitted_at
from profed.topics import followers
from .storage import storage


async def _init() -> None:
    pass


async def _accepted(object_id: str, payload: dict, emitted_at) -> None:
    follower, following = object_id.split("|", 1)
    await (await storage()).accept_edge(following, follower, emitted_at)


async def _deleted(object_id: str, payload: dict, emitted_at) -> None:
    follower, following = object_id.split("|", 1)
    await (await storage()).delete_edge(following, follower, emitted_at)


async def _snapshot(item: dict) -> None:
    if item.get("state") == "accepted" and "accepted_at" in item:
        await (await storage()).accept_edge(item["following"], item["follower"], item["accepted_at"])


followers_handle_events, followers_rebuild, _ = \
    build_projection(topic=followers,
                     subscriber="delivery_splitter",
                     init=_init,
                     on_snapshot_item=_snapshot,
                     on_message_type={"accepted": _accepted,
                                      "deleted": _deleted},
                     event_handler_signature=with_emitted_at)


async def recipients_at(following: str, at) -> set[str]:
    return await (await storage()).recipients_at(following, at)

