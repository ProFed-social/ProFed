# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from datetime import datetime, timezone
from profed.core.persistence.projections import build_projection
from profed.topics import known_accounts
from .storage import storage
 
 
async def _init() -> None:
    await (await storage()).ensure_schema()
 
 
async def _discovered(payload: dict) -> None:
    last = payload["last_webfinger_at"]
    if isinstance(last, str):
        last = datetime.fromisoformat(last)
    await (await storage()).upsert(payload["account_id"],
                                   payload["acct"],
                                   payload["actor_url"],
                                   payload.get("actor_data"),
                                   last)
 
 
handle_events, rebuild, _ = build_projection(topic=known_accounts,
                                             subscriber="api_c2s_known_accounts",
                                             init=_init,
                                             on_snapshot_item=_discovered,
                                             on_message_type={"discovered": _discovered})

