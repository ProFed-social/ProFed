# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.projections import build_projection
from profed.topics import person
from profed.components.api.s2s.actor.storage import storage


async def _init() -> None:
    await (await storage()).ensure_schema()


async def _apply_snapshot_item(data: dict) -> None:
    await (await storage()).upsert(data["preferredUsername"], data)


async def _created(object_id: str, payload: dict) -> None:
    await (await storage()).upsert(object_id, payload)


async def _updated(object_id: str, payload: dict) -> None:
    await (await storage()).upsert(object_id, payload)


async def _deleted(object_id: str, payload: dict) -> None:
    await (await storage()).delete(object_id)


async def _rebuild_finished() -> None:
    (await storage()).rebuild_finished()


handle_user_events, rebuild, reset_last_seen = \
        build_projection(topic=person,
                         init=_init,
                         rebuild_finished=_rebuild_finished,
                         on_snapshot_item=_apply_snapshot_item,
                         on_message_type={"created": _created,
                                          "updated": _updated,
                                          "deleted": _deleted})

