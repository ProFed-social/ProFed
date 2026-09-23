# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional, Dict
from profed.core.message_bus import message_bus
from profed.topics.common import ActivityEvent, validate_payload, validate_verb
from profed.topics.incoming_activities_topic import _KNOWN_VERBS


def validate_local_delivery_event(event_type: str, payload: Dict) -> Optional[Dict]:
    return (None
            if not validate_verb(event_type, _KNOWN_VERBS, "local_delivery") else
            validate_payload(ActivityEvent, payload, "local_delivery"))


def validate_local_delivery_snapshot_item(item) -> Optional[Dict]:
    return None


async def publish_local_delivery(event_type: str, object_id: str, username: str, activity: dict, message_id) -> None:
    async with message_bus().topic("local_delivery").publish() as publish:
        await publish(event_type=event_type,
                      object_id=object_id,
                      payload={"username": username, "activity": activity},
                      message_id=message_id)

topic = {"name":              "local_delivery",
         "validate":          validate_local_delivery_event,
         "snapshot_validate": validate_local_delivery_snapshot_item}

