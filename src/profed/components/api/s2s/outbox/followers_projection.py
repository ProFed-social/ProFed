# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.projections import build_projection
from profed.topics import followers
from .followers_storage import init as init_storage, storage


async def init(config: dict) -> None:
    await init_storage(config)


async def _init() -> None:
    await (await storage()).ensure_schema()


async def _accepted(object_id: str, payload: dict) -> None:
    follower, following = object_id.split("|", 1)
    await (await storage()).add_edge(following, follower)


async def _deleted(object_id: str, payload: dict) -> None:
    follower, following = object_id.split("|", 1)
    await (await storage()).drop_edge(following, follower)


async def _snapshot(item: dict) -> None:
    if item.get("state") == "accepted":
        await (await storage()).add_edge(item["following"], item["follower"])


async def _rebuild_finished() -> None:
    (await storage()).rebuild_finished()


handle_user_events, rebuild, reset_last_seen = build_projection(topic=followers,
                                                                init=_init,
                                                                rebuild_finished=_rebuild_finished,
                                                                on_snapshot_item=_snapshot,
                                                                on_message_type={"accepted": _accepted,
                                                                                 "deleted": _deleted})

