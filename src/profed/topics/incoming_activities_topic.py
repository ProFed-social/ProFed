# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional, Dict
from profed.core.message_bus import message_bus
from profed.models.activity_pub import IncomingActivity
from profed.sanitize import sanitize_document
from profed.topics.common import ActivityEvent, validate_payload, validate_verb


_KNOWN_VERBS = {"Create",
                "Update",
                "Delete",
                "Follow",
                "Accept",
                "Reject",
                "Undo",
                "Like",
                "EmojiReact",
                "Announce",
                "Block"}


REACTION_VERBS = {"Like", "EmojiReact"}


def _undone_type(activity: Dict) -> Optional[str]:
    undone = activity.get("object")
    return undone.get("type") if isinstance(undone, dict) else None


def is_reaction(event_type: str, activity: Dict) -> bool:
    return (event_type in REACTION_VERBS
            if event_type != "Undo" else
            _undone_type(activity) in REACTION_VERBS)


def validate_incoming_activities_event(event_type: str, payload: Dict) -> Optional[Dict]:
    return (None
            if not validate_verb(event_type, _KNOWN_VERBS, "incoming_activities") else
            validate_payload(ActivityEvent, payload, "incoming_activities"))


def validate_incoming_activities_snapshot_item(item) -> Optional[Dict]:
    return None


def canonical_incoming(activity: dict) -> tuple[str, str, dict]:
    canonical = IncomingActivity.model_validate(activity).model_dump(by_alias=True, exclude_none=True)
    return (canonical["type"],
            canonical["id"],
            sanitize_document({key: value for key, value in canonical.items() if key not in ("type", "id")}))


async def publish_incoming(event_type: str, object_id: str, username: str, activity: dict, message_id=None) -> None:
    async with message_bus().topic("incoming_activities").publish() as publish:
        await publish(event_type=event_type,
                      object_id=object_id,
                      payload={"username": username, "activity": activity},
                      message_id=message_id)

topic = {"name":              "incoming_activities",
         "validate":          validate_incoming_activities_event,
         "snapshot_validate": validate_incoming_activities_snapshot_item}

