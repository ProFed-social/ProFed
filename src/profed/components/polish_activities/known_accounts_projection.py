# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.projections import build_projection
from profed.topics import known_accounts
from .storage import storage


async def _init() -> None:
    pass


async def _store(object_id: str, payload: dict) -> None:
    await (await storage()).upsert(int(object_id), payload["acct"], payload["url"])


async def _deleted(object_id: str, payload: dict) -> None:
    await (await storage()).delete(int(object_id))


async def _apply_snapshot_item(item: dict) -> None:
    await (await storage()).upsert(int(item["id"]), item["acct"], item["url"])


async def _rebuild_finished() -> None:
    (await storage()).rebuild_finished()


known_accounts_handle_events, known_accounts_rebuild, _ = \
    build_projection(topic=known_accounts,
                     init=_init,
                     rebuild_finished=_rebuild_finished,
                     on_snapshot_item=_apply_snapshot_item,
                     on_message_type={"created": _store,
                                      "updated": _store,
                                      "deleted": _deleted})

