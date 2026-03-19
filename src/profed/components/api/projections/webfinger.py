# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.projections import build_projection
from profed.topics import users
from profed.components.api.storage.webfinger_users import storage


async def _init() -> None:
    store = await storage()
    await store.ensure_table()


async def _apply_snapshot_item(data: dict) -> None:
    store = await storage()
    await store.add(data["username"])


async def _created(data: dict) -> None:
    store = await storage()
    await store.add(data["username"])


async def _deleted(data: dict) -> None:
    store = await storage()
    await store.delete(data["username"])

handle_user_events, rebuild, reset_last_seen = \
        build_projection(topic=users,
                         init=_init,
                         on_snapshot_item=_apply_snapshot_item,
                         on_message_type={"created": _created,
                                          "deleted": _deleted})

