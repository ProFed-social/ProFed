# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.projections import build_projection
from profed.topics import followers as followers_topic
from profed.identity import account_id
from .storage import storage


async def _init() -> None:
    await (await storage()).ensure_schema()


def _edge(object_id: str) -> tuple[str, int, str, int]:
    follower, following = object_id.split("|", 1)
    return follower, int(account_id(follower)), following, int(account_id(following))


async def _upsert(object_id: str, payload: dict, state: str) -> None:
    follower, follower_id, following, following_id = _edge(object_id)
    await (await storage()).upsert(follower,
                                   follower_id,
                                   following,
                                   following_id,
                                   state,
                                   payload.get("follow_activity_id"))


async def _requested(object_id: str, payload: dict) -> None:
    await _upsert(object_id, payload, "requested")


async def _accepted(object_id: str, payload: dict) -> None:
    await _upsert(object_id, payload, "accepted")


async def _removed(object_id: str, payload: dict) -> None:
    follower, _, following, _ = _edge(object_id)
    await (await storage()).delete(follower, following)


async def _snapshot(item: dict) -> None:
    state = item.get("state", "accepted")
    if state not in ("requested", "accepted"):
        return
    await (await storage()).upsert(item["follower"],
                                   int(account_id(item["follower"])),
                                   item["following"],
                                   int(account_id(item["following"])),
                                   state,
                                   item.get("follow_activity_id"))


async def _rebuild_finished() -> None:
    (await storage()).rebuild_finished()


handle_events, rebuild, _ = \
    build_projection(topic=followers_topic,
                     subscriber="api_c2s_follows",
                     init=_init,
                     rebuild_finished=_rebuild_finished,
                     on_snapshot_item=_snapshot,
                     on_message_type={"requested": _requested,
                                      "accepted": _accepted,
                                      "rejected": _removed,
                                      "deleted": _removed})

