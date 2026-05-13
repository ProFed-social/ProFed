# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.projections import build_projection
from profed.topics import followers as followers_topic
from .storage import storage


async def _init() -> None:
    await (await storage()).ensure_schema()


async def _follower_created(payload: dict) -> None:
    await (await storage()).add_follower(payload["following"],
                                         payload["follower"])


async def _follower_deleted(payload: dict) -> None:
    await (await storage()).remove_follower(payload["following"],
                                            payload["follower"])


handle_events, rebuild, _ = build_projection(
    topic=            followers_topic,
    subscriber=       "api_c2s_followers",
    init=             _init,
    on_snapshot_item= _follower_created,
    on_message_type=  {"created": _follower_created,
                       "deleted": _follower_deleted})

