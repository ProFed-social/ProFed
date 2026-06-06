# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from profed.core.persistence.projections import build_projection
from profed.topics import known_accounts
from .storage import storage
 
 
async def _init() -> None:
    await (await storage()).ensure_schema()
 
 
async def _follow_requested(object_id: str, payload: dict) -> None:
    await (await storage()).upsert(int(object_id),
                                   payload["following_user"],
                                   False,
                                   payload.get("follow_activity_id"))


async def _follow_accepted(object_id: str, payload: dict) -> None:
    await (await storage()).upsert(int(object_id), payload["following_user"], True)


async def _unfollow(object_id: str, payload: dict) -> None:
    await (await storage()).delete(int(object_id), payload["following_user"])


async def _rebuild_finished() -> None:
    (await storage()).rebuild_finished()


handle_events, rebuild, _ = \
    build_projection(topic=known_accounts,
                     subscriber="api_c2s_following",
                     init=_init,
                     rebuild_finished=_rebuild_finished,
                     on_snapshot_item=None,
                     on_message_type={"follow_requested": _follow_requested,
                                      "follow_accepted": _follow_accepted,
                                      "unfollow": _unfollow})

