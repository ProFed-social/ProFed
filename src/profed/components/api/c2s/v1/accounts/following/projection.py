# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from profed.core.projections import build_projection
from profed.topics import known_accounts
from .storage import storage
 
 
async def _init() -> None:
    await (await storage()).ensure_table()
 
 
async def _follow_requested(payload: dict) -> None:
    await (await storage()).upsert(payload["account_id"],
                                   payload["following_user"],
                                   False)
 
 
async def _follow_accepted(payload: dict) -> None:
    await (await storage()).upsert(payload["account_id"],
                                   payload["following_user"],
                                   True)
 
 
async def _follow_retracted(payload: dict) -> None:
    await (await storage()).delete(payload["account_id"],
                                   payload["following_user"])
 
 
handle_events, rebuild, _ = \
    build_projection(topic=known_accounts,
                     subscriber="api_c2s_following",
                     init=_init,
                     on_snapshot_item=None,
                     on_message_type={"follow_requested": _follow_requested,
                                      "follow_accepted":  _follow_accepted,
                                      "follow_retracted": _follow_retracted})

