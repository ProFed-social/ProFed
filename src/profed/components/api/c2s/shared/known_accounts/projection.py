# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from datetime import datetime, timezone
from profed.core.persistence.projections import build_projection
from profed.topics import known_accounts
from .storage import storage
 
 
async def _init() -> None:
    await (await storage()).ensure_schema()


async def _store(account_id: int,
                 acct:       str,
                 actor_url:  str,
                 actor_data: dict | None,
                 last:       str | datetime) -> None:
    if isinstance(last, str):
        last = datetime.fromisoformat(last)
    await (await storage()).upsert(account_id, acct, actor_url, actor_data, last)


async def _discovered(object_id: str, payload: dict) -> None:
    await _store(int(object_id),
                 payload["acct"],
                 payload["actor_url"],
                 payload.get("actor_data"),
                 payload["last_webfinger_at"])


async def _discovered_snapshot(item: dict) -> None:
    await _store(item["account_id"],
                 item["acct"],
                 item["actor_url"],
                 item.get("actor_data"),
                 item["last_webfinger_at"])


handle_events, rebuild, _ = build_projection(topic=known_accounts,
                                             subscriber="api_c2s_known_accounts",
                                             init=_init,
                                             on_snapshot_item=_discovered_snapshot,
                                             on_message_type={"discovered": _discovered})

