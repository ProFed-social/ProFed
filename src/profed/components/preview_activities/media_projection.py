# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.projections import build_projection
from profed.topics import media
from profed.util import noop
from .storage import storage


async def _init() -> None:
    await (await storage()).ensure_schema()


async def _uploaded(object_id: str, payload: dict) -> None:
    measures = payload.get("metadata") or {}
    await (await storage()).remember(object_id,
                                     payload["url"],
                                     payload["content_type"],
                                     measures.get("width"),
                                     measures.get("height"))


async def _deleted(object_id: str, payload: dict) -> None:
    await (await storage()).forget(object_id)


async def _variants_added(object_id: str, payload: dict) -> None:
    for variant in payload:
        await (await storage()).note_variant(object_id, variant)


async def _rebuild_finished() -> None:
    (await storage()).rebuild_finished()


handle_events, rebuild, _ = build_projection(topic=media,
                                             init=_init,
                                             rebuild_finished=_rebuild_finished,
                                             on_snapshot_item=noop,
                                             on_message_type={"uploaded": _uploaded,
                                                              "deleted": _deleted,
                                                              "variants_added": _variants_added})

