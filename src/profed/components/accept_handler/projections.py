# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from profed.core.persistence.projections import build_projection
from profed.topics import known_accounts
from .storage import storage
 
 
async def _init() -> None:
    await (await storage()).ensure_schema()
 
 
async def _discovered(payload: dict) -> None:
    await (await storage()).upsert(
        payload["actor_url"],
        payload["account_id"])
 
 
handle_events, rebuild, _ = \
    build_projection(topic=known_accounts,
                     subscriber="accept_handler",
                     init=_init,
                     on_snapshot_item=_discovered,
                     on_message_type={"discovered": _discovered})

