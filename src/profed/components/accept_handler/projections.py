# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from profed.core.persistence.projections import build_projection
from profed.topics import known_accounts
from .storage import storage
 
 
async def _init() -> None:
    await (await storage()).ensure_schema()
 
 
async def _store(payload: dict) -> None:
    await (await storage()).upsert(payload["url"], int(payload["id"]))


async def _created(object_id: str, payload: dict) -> None:
    await _store(payload)


async def _updated(object_id: str, payload: dict) -> None:
    await _store(payload)


async def _snapshot(item: dict) -> None:
    await _store(item)


async def _rebuild_finished() -> None:
    (await storage()).rebuild_finished()


handle_events, rebuild, _ = \
    build_projection(topic=known_accounts,
                     subscriber="accept_handler",
                     init=_init,
                     rebuild_finished=_rebuild_finished,
                     on_snapshot_item=_snapshot,
                     on_message_type={"created": _created,
                                      "updated": _updated})

