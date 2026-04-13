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


def _activity_from_user_event(event_type: str, payload: dict):
    actor = Person.from_user(UserProfile.model_validate(payload))
    actor_dict = actor.model_dump(by_alias=True, exclude_none=True)

    activities = {"created": (CreateActivity, "create"),
                  "updated": (UpdateActivity, "update")}
    return (activities[event_type][0](id=f"{actor.id}#{activities[event_type][1]}",
                                      actor=actor.id,
                                      object=actor_dict)
            if event_type in activities else
            None)


async def handle_user_events() -> None:
    async for sequence_id, event \
            in message_bus().topic("users").subscribe(_SUBSCRIBER,
                                                      0,
                                                      include_sequence_id=True):
        event_type, payload = users_topic["validate"](event)

        if event_type not in ("created", "updated") or payload is None:
            continue

        try:
            activity = _activity_from_user_event(event_type, payload)
        except Exception as exc:
            logger.warning("Ignoring malformed users event in user_activities: %r; %s",
                           payload,
                           exc)
            continue

        async with message_bus().topic("activities").publish() as publish:
            await publish({"type": "created",
                           "payload": {"username": payload["username"],
                                       **activity.model_dump(by_alias=True,
                                                             exclude_none=True)}},
                          message_id=_USERS_SOURCE.message_id(sequence_id))

