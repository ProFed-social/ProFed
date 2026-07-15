# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.projections import build_projection
from profed.topics import resolved_activities
from profed.components.api.c2s.v1.timelines.storage import storage


async def _init() -> None:
    store = await storage()
    await store.ensure_schema()


def _inner_object_id(activity: dict) -> str | None:
    obj = activity.get("object")
    if isinstance(obj, str):
        return obj

    if isinstance(obj, dict):
        return obj.get("id")

    return None


async def _apply_item(data: dict) -> None:
    activity  = data["activity"]
    status_id = _inner_object_id(activity) or activity.get("id")
    if status_id is None:
        return

    await (await storage()).add(data["username"], status_id, activity)


async def _on_create(object_id: str, payload: dict) -> None:
    activity  = {"id": object_id, "type": "Create", **payload["activity"]}
    status_id = _inner_object_id(activity)
    if status_id is None:
        return

    await (await storage()).add(payload["username"], status_id, activity)


async def _on_update(object_id: str, payload: dict) -> None:
    activity  = {"id": object_id, "type": "Update", **payload["activity"]}
    status_id = _inner_object_id(activity)
    if status_id is None:
        return

    await (await storage()).update_status(payload["username"], status_id, activity)


async def _on_delete(object_id: str, payload: dict) -> None:
    activity  = {"id": object_id, "type": "Delete", **payload["activity"]}
    status_id = _inner_object_id(activity)
    if status_id is None:
        return

    await (await storage()).delete_status(payload["username"], status_id)


async def _on_announce(object_id: str, payload: dict) -> None:
    activity = {"id": object_id, "type": "Announce", **payload["activity"]}

    await (await storage()).add(payload["username"], object_id, activity)


async def _rebuild_finished() -> None:
    (await storage()).rebuild_finished()


handle_events, rebuild, _ = \
    build_projection(topic=resolved_activities,
                     subscriber="api_home_timeline",
                     init=_init,
                     rebuild_finished=_rebuild_finished,
                     on_snapshot_item=_apply_item,
                     on_message_type={"Create": _on_create,
                                      "Update": _on_update,
                                      "Delete": _on_delete,
                                      "Announce": _on_announce})

