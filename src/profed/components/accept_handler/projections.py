# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from profed.core.persistence.projections import build_projection
from profed.topics import known_accounts
from .storage import storage
 
 
async def _init() -> None:
    await (await storage()).ensure_schema()
 
 
async def _discovered(object_id: str, payload: dict) -> None:
    await (await storage()).upsert(payload["actor_url"], int(object_id))


async def _discovered_snapshot(item: dict) -> None:
    await (await storage()).upsert(item["actor_url"], item["account_id"])
 
 
handle_events, rebuild, _ = \
    build_projection(topic=known_accounts,
                     subscriber="accept_handler",
                     init=_init,
                     on_snapshot_item=_discovered_snapshot,
                     on_message_type={"discovered": _discovered})

