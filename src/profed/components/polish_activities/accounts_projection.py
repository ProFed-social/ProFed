# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.projections import build_projection
from profed.topics import accounts
from .storage import storage


async def _init() -> None:
    pass


async def _apply_snapshot_item(item: dict) -> None:
    await (await storage()).add(item["username"])


async def _present(object_id: str, payload: dict) -> None:
    await (await storage()).add(object_id)


async def _deleted(object_id: str, payload: dict) -> None:
    await (await storage()).delete(object_id)


async def _rebuild_finished() -> None:
    (await storage()).rebuild_finished()


accounts_handle_events, accounts_rebuild, _ = \
    build_projection(topic=accounts,
                     init=_init,
                     rebuild_finished=_rebuild_finished,
                     on_snapshot_item=_apply_snapshot_item,
                     on_message_type={"created": _present,
                                      "updated": _present,
                                      "deleted": _deleted})

