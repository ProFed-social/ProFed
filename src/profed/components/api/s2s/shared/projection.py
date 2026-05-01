# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.projections import build_projection
from profed.topics import users


def build_users_projection(storage):
    async def _init() -> None:
        nonlocal storage

        store = await storage()
        await store.ensure_schema()


    async def _apply_snapshot_item(data: dict) -> None:
        nonlocal storage

        store = await storage()
        await store.add(data["username"])


    async def _created(data: dict) -> None:
        nonlocal storage

        store = await storage()
        await store.add(data["username"])


    async def _deleted(data: dict) -> None:
        nonlocal storage

        store = await storage()
        await store.delete(data["username"])

    return build_projection(topic=users,
                            subscriber="api",
                            init=_init,
                            on_snapshot_item=_apply_snapshot_item,
                            on_message_type={"created": _created,
                                             "deleted": _deleted})

