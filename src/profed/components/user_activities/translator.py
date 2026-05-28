# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging

from profed.core.message_bus import message_bus
from profed.core.message_bus.source_key import source_key
from profed.topics import users as users_topic
from profed.models import UserProfile
from profed.models.activity_pub import Person, CreateActivity, UpdateActivity


logger = logging.getLogger(__name__)
_USERS_SOURCE = source_key("users")
_SUBSCRIBER = "user_activities"
_ACTIVITY_FOR = {"created": (CreateActivity, "create"),
                 "updated": (UpdateActivity, "update")}

def _activity_from_user_event(event_type: str, username: str, payload: dict):
    cls, verb = _ACTIVITY_FOR[event_type]
    actor = Person.from_user(UserProfile.model_validate({**payload, "username": username}))
    return cls(id=f"{actor.id}#{verb}",
               actor=actor.id,
               object=actor.model_dump(by_alias=True, exclude_none=True))


async def handle_user_events() -> None:
    async for sequence_id, event_type, username, _, payload \
              in message_bus().topic("users").subscribe(_SUBSCRIBER, 0):
        if event_type not in _ACTIVITY_FOR:
            continue

        validated = users_topic["validate"](event_type, payload)
        if validated is None:
            continue

        try:
            activity = _activity_from_user_event(event_type, username, validated)
        except Exception as exc:
            logger.warning("Ignoring malformed users event in user_activities: %r; %s",
                           payload,
                           exc)
            continue

        async with message_bus().topic("activities").publish() as publish:
            await publish(event_type=activity.type,
                          object_id=activity.id,
                          payload={"username": username,
                                   "activity": activity.as_event_payload()},
                          message_id=_USERS_SOURCE.message_id(sequence_id))

