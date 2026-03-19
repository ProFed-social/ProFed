# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.projections import build_projection
from profed.topics import activities
from profed.components.api.storage.outbox import storage


async def _init() -> None:
    store = await storage()
    await store.ensure_table()


async def _apply_item(data: dict) -> None:
    store = await storage()
    await store.add(data["username"], data)


async def _created(data: dict) -> None:
    store = await storage()
    await store.add(data["username"], data)


handle_activities, rebuild, reset_last_seen = \
        build_projection(topic=activities,
                         init=_init,
                         on_snapshot_item=_apply_item,
                         on_message_type={"created": _created})

