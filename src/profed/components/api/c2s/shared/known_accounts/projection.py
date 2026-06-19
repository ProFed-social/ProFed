# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from datetime import datetime
from profed.core.persistence.projections import build_projection
from profed.topics import known_accounts
from .storage import storage
from .service import make_account
 
 
async def _init() -> None:
    await (await storage()).ensure_schema()


async def _store(account_id: int, payload: dict) -> None:
    account = make_account(payload)
    last = payload["last_webfinger_at"]
    await (await storage()).upsert(account_id,
                                   account.acct,
                                   account.url,
                                   account.model_dump(),
                                   (datetime.fromisoformat(last)
                                    if isinstance(last, str) else
                                    last))


async def _discovered(object_id: str, payload: dict) -> None:
    await _store(int(object_id), payload)


async def _discovered_snapshot(item: dict) -> None:
    await _store(item["account_id"], item)


async def _rebuild_finished() -> None:
    (await storage()).rebuild_finished()


handle_events, rebuild, _ = build_projection(topic=known_accounts,
                                             subscriber="api_c2s_known_accounts",
                                             init=_init,
                                             rebuild_finished=_rebuild_finished,
                                             on_snapshot_item=_discovered_snapshot,
                                             on_message_type={"discovered": _discovered})

