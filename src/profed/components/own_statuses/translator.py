# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.message_bus import message_bus
from profed.core.message_bus.source_key import source_key
from profed.core.persistence.projections import build_projection, with_event_type, with_sequence_id
from profed.models.mastodon import Status
from profed.topics import activities
from profed.topics.statuses_topic import STATUS_VERBS
from profed.util import noop


_ACTIVITIES_SOURCE = source_key("activities")
_ACTOR_TYPES = {"Person",
                "Service",
                "Group",
                "Organization",
                "Application"}


def _inner_object_id(activity: dict) -> str | None:
    obj = activity.get("object")
    return (obj
            if isinstance(obj, str) else
            obj.get("id")
            if isinstance(obj, dict) else
            None)


def _is_actor_object(activity: dict) -> bool:
    obj = activity.get("object")
    return isinstance(obj, dict) and obj.get("type") in _ACTOR_TYPES


def status_id_of(event_type: str, object_id: str, activity: dict) -> str | None:
    return object_id if event_type == "Announce" else _inner_object_id(activity)


def mastodon_id_of(sequence_id: int) -> str:
    return str(_ACTIVITIES_SOURCE.message_id(sequence_id).int)


async def _publish(event_type: str, object_id: str, payload: dict, sequence_id: int) -> None:
    async with message_bus().topic("statuses").publish() as publish:
        await publish(event_type=event_type,
                      object_id=object_id,
                      payload=payload,
                      message_id=_ACTIVITIES_SOURCE.message_id(sequence_id))


async def _convert(event_type: str, object_id: str, payload: dict, sequence_id: int) -> None:
    activity = {"id": object_id, "type": event_type, **payload["activity"]}
    status_id = status_id_of(event_type, object_id, activity)
    if status_id is None or _is_actor_object(activity):
        return

    status = Status.from_activity(activity, id=mastodon_id_of(sequence_id))
    await _publish(event_type,
                   object_id,
                   {"username": payload["username"],
                    "status_id": status_id,
                    "status": status.model_dump(exclude={"account"})},
                   sequence_id)


async def _convert_delete(event_type: str, object_id: str, payload: dict, sequence_id: int) -> None:
    activity = {"id": object_id, "type": event_type, **payload["activity"]}
    status_id = _inner_object_id(activity)
    if status_id is None:
        return

    await _publish(event_type, object_id, {"username": payload["username"], "status_id": status_id}, sequence_id)


handle_events, rebuild, _ = \
    build_projection(topic=activities,
                     init=noop,
                     on_snapshot_item=noop,
                     on_message_type={verb: (_convert_delete
                                             if verb == "Delete" else
                                             _convert)
                                      for verb in STATUS_VERBS},
                     event_handler_signature=with_event_type & with_sequence_id)

