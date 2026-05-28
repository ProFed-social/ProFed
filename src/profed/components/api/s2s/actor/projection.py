# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.projections import build_projection
from profed.topics import users
from profed.components.api.s2s.actor.storage import storage


async def _init() -> None:
    store = await storage()
    await store.ensure_schema()


async def _apply_snapshot_item(data: dict) -> None:
    store = await storage()
    await store.add(data["username"], data)


async def _created(object_id: str, payload: dict) -> None:
    store = await storage()
    await store.add(object_id, {**payload, "username": object_id})


async def _updated(object_id: str, payload: dict) -> None:
    store = await storage()
    await store.update(object_id, {**payload, "username": object_id})


async def _deleted(object_id: str, payload: dict) -> None:
    store = await storage()
    await store.delete(object_id)


handle_user_events, rebuild, reset_last_seen = \
        build_projection(topic=users,
                         subscriber="api",
                         init=_init,
                         on_snapshot_item=_apply_snapshot_item,
                         on_message_type={"created": _created,
                                          "updated": _updated,
                                          "deleted": _deleted })

