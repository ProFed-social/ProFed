# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.projections import build_projection
from profed.topics import followers as followers_topic
from .storage import storage


async def _init() -> None:
    await (await storage()).ensure_schema()


async def _follower_created(object_id: str, payload: dict) -> None:
    follower, following = object_id.split("|", 1)
    await (await storage()).add_follower(following, follower)


async def _follower_deleted(object_id: str, payload: dict) -> None:
    follower, following = object_id.split("|", 1)
    await (await storage()).remove_follower(following, follower)


async def _follower_snapshot(item: dict) -> None:
    await (await storage()).add_follower(item["following"], item["follower"])


async def _rebuild_finished() -> None:
    (await storage()).rebuild_finished()


handle_events, rebuild, _ = build_projection(topic=followers_topic,
                                             subscriber="api_c2s_followers",
                                             init=_init,
                                             rebuild_finished=_rebuild_finished,
                                             on_snapshot_item=_follower_snapshot,
                                             on_message_type={"created": _follower_created,
                                                              "deleted": _follower_deleted})

