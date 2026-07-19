# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.projections import build_projection, with_sequence_id
from profed.topics import activities
from profed.components.api.c2s.v1.accounts.statuses.storage import storage


async def _init() -> None:
    store = await storage()
    await store.ensure_schema()


def _inner_object_id(activity: dict) -> str | None:
    obj = activity.get("object")
    if isinstance(obj, str):
        return obj

    if isinstance(obj, dict):
        return obj.get("id")


def _is_actor_object(activity: dict) -> bool:
    obj = activity.get("object")
    return (isinstance(obj, dict) and
            obj.get("type") in {"Person",
                                "Service",
                                "Group",
                                "Organization",
                                "Application"})


async def _apply_item(data: dict) -> None:
    activity = data["activity"]
    if _is_actor_object(activity):
        return

    status_id = _inner_object_id(activity) or activity.get("id")
    if status_id is None:
        return

    await (await storage()).add(data["username"],
                                status_id,
                                data.get("sequence_id", 0),
                                activity)


async def _on_create(object_id: str, payload: dict, sequence_id: int) -> None:
    activity = {"id": object_id, "type": "Create", **payload["activity"]}
    if _is_actor_object(activity):
        return

    status_id = _inner_object_id(activity)
    if status_id is None:
        return

    await (await storage()).add(payload["username"], status_id, sequence_id, activity)


async def _on_update(object_id: str, payload: dict, sequence_id: int) -> None:
    activity = {"id": object_id, "type": "Update", **payload["activity"]}
    if _is_actor_object(activity):
        return

    status_id = _inner_object_id(activity)
    if status_id is None:
        return

    await (await storage()).update_status(payload["username"], status_id, activity)


async def _on_delete(object_id: str, payload: dict, sequence_id: int) -> None:
    activity = {"id": object_id, "type": "Delete", **payload["activity"]}
    status_id = _inner_object_id(activity)
    if status_id is None:
        return

    await (await storage()).delete_status(payload["username"], status_id)


async def _on_announce(object_id: str, payload: dict, sequence_id: int) -> None:
    activity = {"id": object_id, "type": "Announce", **payload["activity"]}

    await (await storage()).add(payload["username"], object_id, sequence_id, activity)


async def _rebuild_finished() -> None:
    (await storage()).rebuild_finished()


handle_events, rebuild, _ = \
    build_projection(topic=activities,
                     init=_init,
                     rebuild_finished=_rebuild_finished,
                     on_snapshot_item=_apply_item,
                     on_message_type={"Create": _on_create,
                                      "Update": _on_update,
                                      "Delete": _on_delete,
                                      "Announce": _on_announce},
                     event_handler_signature=with_sequence_id)

