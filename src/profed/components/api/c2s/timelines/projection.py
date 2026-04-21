# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from profed.core.projections import build_projection
from profed.topics import incoming_activities
from .storage import storage
 
 
async def _init() -> None:
    store = await storage()
    await store.ensure_table()
 
 
async def _apply_item(data: dict) -> None:
    store = await storage()
    await store.add(data["username"], data["activity"])
 
 
async def _incoming(data: dict) -> None:
    store = await storage()
    await store.add(data["username"], data["activity"])
 
 
handle_events, rebuild, _ = \
    build_projection(topic=incoming_activities,
                     subscriber="api_home_timeline",
                     init=_init,
                     on_snapshot_item=_apply_item,
                     on_message_type={"incoming": _incoming})

