# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import Optional, Dict
from profed.identity import status_id
from profed.models.mastodon import Status
from profed.topics.common import StatusEvent, validate_payload, validate_verb


STATUS_VERBS = {"Create",
                "Update",
                "Delete",
                "Announce"}

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


def inner_object_id(activity: dict) -> str | None:
    obj = activity.get("object")
    return (obj
            if isinstance(obj, str) else
            obj.get("id")
            if isinstance(obj, dict) else
            None)


def is_actor_object(activity: dict) -> bool:
    obj = activity.get("object")
    return isinstance(obj, dict) and obj.get("type") in _ACTOR_TYPES


def object_key_of(event_type: str, object_id: str, activity: dict) -> str | None:
    return object_id if event_type == "Announce" else inner_object_id(activity)


def status_event(event_type: str,
                 object_id: str,
                 payload: dict,
                 emitted_at: datetime,
                 sequence_id: int,
                 own: bool) -> dict | None:
    activity = {"id": object_id, "type": event_type, **payload["activity"]}
    object_key = object_key_of(event_type, object_id, activity)
    if object_key is None or is_actor_object(activity):
        return None

    return {"username": payload["username"],
            "status_id": object_key,
            "actor_url": activity.get("actor", ""),
            "status": Status.from_activity(activity,
                                           id=status_id(emitted_at,
                                                        sequence_id, own=own)).model_dump(exclude={"account"})}


def delete_event(event_type: str, object_id: str, payload: dict) -> dict | None:
    object_key = inner_object_id({"id": object_id, "type": event_type, **payload["activity"]})
    return (None
            if object_key is None else
            {"username": payload["username"], "status_id": object_key})


topic = {"name": "statuses",
         "validate": validate_statuses_event,
         "snapshot_validate": validate_statuses_snapshot_item}

