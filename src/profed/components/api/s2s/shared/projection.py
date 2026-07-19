# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.projections import build_projection
from profed.topics import person


def build_person_projection(storage):
    async def _init() -> None:
        nonlocal storage

        store = await storage()
        await store.ensure_schema()

    async def _apply_snapshot_item(data: dict) -> None:
        nonlocal storage

        store = await storage()
        await store.add(data["preferredUsername"])

    async def _created(object_id: str, payload: dict) -> None:
        nonlocal storage

        store = await storage()
        await store.add(object_id)

    async def _deleted(object_id: str, payload: dict) -> None:
        nonlocal storage

        store = await storage()
        await store.delete(object_id)

    async def _rebuild_finished() -> None:
        (await storage()).rebuild_finished()

    return build_projection(topic=person,
                            init=_init,
                            rebuild_finished=_rebuild_finished,
                            on_snapshot_item=_apply_snapshot_item,
                            on_message_type={"created": _created,
                                             "deleted": _deleted})

