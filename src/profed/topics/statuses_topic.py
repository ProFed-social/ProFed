# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import Optional, Dict
from profed.identity import status_id
from profed.models.activity_pub.activity_streams import ActivityStreamsObject
from profed.models.mastodon import Status
from profed.topics.common import StatusEvent, validate_payload, validate_verb


STATUS_VERBS = {"Create",
                "Update",
                "Delete",
                "Announce",
                "Like"}

_KEYED_BY_ACTIVITY = {"Announce", "Like"}

_UNDOABLE_TYPES = {"Announce", "Like", "EmojiReact"}

_ACTOR_TYPES = {"Person",
                "Service",
                "Group",
                "Organization",
                "Application"}


def validate_statuses_event(event_type: str, payload: Dict) -> Optional[Dict]:
    return (None
            if not validate_verb(event_type, STATUS_VERBS, "statuses") else
            validate_payload(StatusEvent, payload, "statuses"))


def validate_statuses_snapshot_item(item) -> Optional[Dict]:
    return None


def inner_object_id(obj) -> str | None:
    return (obj
            if isinstance(obj, str) else
            obj.get("id")
            if isinstance(obj, dict) else
            None)


def is_actor_object(obj) -> bool:
    return isinstance(obj, dict) and obj.get("type") in _ACTOR_TYPES


def is_undoable_object(obj) -> bool:
    return isinstance(obj, dict) and obj.get("type") in _UNDOABLE_TYPES


def object_key_of(event_type: str, object_id: str, activity: dict) -> str | None:
    return object_id if event_type in _KEYED_BY_ACTIVITY else inner_object_id(activity.get("object"))


def reaction_emoji(activity: dict) -> str:
    return activity.get("content") or activity.get("_misskey_reaction") or ""


def reference_of(event_type: str, activity: dict) -> dict | None:
    url = (inner_object_id(activity.get("object"))
           if event_type == "Announce" else
           next((reference.url
                 for reference in ActivityStreamsObject.model_validate(activity).referenced_objects()),
                None))
    return {"kind": "announce" if event_type == "Announce" else "reply", "url": url} if url else None


def status_event(event_type: str,
                 object_id: str,
                 payload: dict,
                 emitted_at: datetime,
                 sequence_id: int,
                 own: bool) -> dict | None:
    activity = {"id": object_id, "type": event_type, **payload["activity"]}
    object_key = object_key_of(event_type, object_id, activity)
    if object_key is None or is_actor_object(activity.get("object")):
        return None

    return {"username": payload["username"],
            "status_id": object_key,
            "actor_url": activity.get("actor", ""),
            "reference": reference_of(event_type, activity),
            "status": Status.from_activity(activity,
                                           id=status_id(emitted_at,
                                                        sequence_id, own=own)).model_dump(exclude={"account"})}


def reaction_event(event_type: str,
                   object_id: str,
                   payload: dict,
                   emitted_at: datetime,
                   sequence_id: int,
                   own: bool) -> dict | None:
    activity = {"id": object_id, "type": event_type, **payload["activity"]}
    target = inner_object_id(activity.get("object"))
    return (None
            if target is None or is_actor_object(activity.get("object")) else
            {"username": payload["username"],
             "status_id": object_id,
             "actor_url": activity.get("actor", ""),
             "reference": {"kind": "like", "url": target, "emoji": reaction_emoji(activity)},
             "status": {"id": status_id(emitted_at, sequence_id, own=own)}})


def delete_event(event_type: str, object_id: str, payload: dict) -> dict | None:
    object_key = inner_object_id({"id": object_id, "type": event_type, **payload["activity"]}.get("object"))
    return (None
            if object_key is None else
            {"username": payload["username"], "status_id": object_key})


def undo_event(event_type: str, object_id: str, payload: dict) -> dict | None:
    return (delete_event(event_type, object_id, payload)
            if is_undoable_object(payload["activity"].get("object")) else
            None)


topic = {"name": "statuses",
         "validate": validate_statuses_event,
         "snapshot_validate": validate_statuses_snapshot_item}

