# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.projections import build_projection
from profed.topics import resolved_activities
from profed.topics.statuses_topic import inner_object_id
from profed.util import noop
from . import fetch
from .storage import storage


def _object_of(payload: dict):
    inner = (payload.get("activity") or {}).get("object")
    return inner if isinstance(inner, dict) else None


async def _on_object(object_id: str, payload: dict) -> None:
    obj = _object_of(payload)
    url = inner_object_id(obj) if obj is not None else None
    collection_url = fetch.collection_url(obj) if obj is not None else None

    if url and collection_url:
        await (await storage()).remember(url, collection_url)


async def _on_delete(object_id: str, payload: dict) -> None:
    await (await storage()).forget(object_id)


async def _rebuild_finished() -> None:
    (await storage()).rebuild_finished()


handle_events, rebuild, _ = build_projection(topic=resolved_activities,
                                             init=noop,
                                             rebuild_finished=_rebuild_finished,
                                             on_snapshot_item=noop,
                                             on_message_type={"Create": _on_object,
                                                              "Update": _on_object,
                                                              "Delete": _on_delete})

