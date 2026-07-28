# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional, Dict
from profed.core.message_bus import message_bus
from profed.topics.common import ActivityEvent, validate_payload, validate_verb


_KNOWN_VERBS = {"Create",
                "Update",
                "Delete",
                "Follow",
                "Accept",
                "Reject",
                "Undo",
                "Like",
                "Announce",
                "Block"}


def validate_incoming_activities_event(event_type: str, payload: Dict) -> Optional[Dict]:
    return (None
            if not validate_verb(event_type, _KNOWN_VERBS, "incoming_activities") else
            validate_payload(ActivityEvent, payload, "incoming_activities"))


def validate_incoming_activities_snapshot_item(item) -> Optional[Dict]:
    return None


async def publish_incoming(event_type: str, object_id: str, username: str, activity: dict) -> None:
    async with message_bus().topic("incoming_activities").publish() as publish:
        await publish(event_type=event_type, object_id=object_id, payload={"username": username, "activity": activity})


topic = {"name":              "incoming_activities",
         "validate":          validate_incoming_activities_event,
         "snapshot_validate": validate_incoming_activities_snapshot_item}

