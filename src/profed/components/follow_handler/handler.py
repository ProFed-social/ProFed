# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging

from profed.core.message_bus import message_bus
from profed.core.message_bus.source_key import source_key
from profed.topics import incoming_activities
from profed.identity import actor_url_from_username
from profed.models.activity_pub import (AcceptActivity,
                                        FollowActivity,
                                        UndoFollowActivity)


logger = logging.getLogger(__name__)
_source_key = source_key("incoming_activities")


async def _handle_follow(username: str, activity: dict, seq: int) -> None:
    try:
        follow = FollowActivity.model_validate(activity)
    except Exception as e:
        logger.warning("Invalid Follow activity: %r – error: %s", activity, e)
        return

    local_actor_url = actor_url_from_username(username)

    async with message_bus().topic("followers").publish() as publish:
        await publish(event_type="accepted",
                      object_id=f"{follow.actor}|{local_actor_url}",
                      payload={},
                      message_id=_source_key.message_id(seq))

    logger.info("follow_handler: published follower %r -> %r", follow.actor, local_actor_url)
    accept = AcceptActivity(id=f"{follow.id}#accepts/",
                            actor=local_actor_url,
                            object=follow.model_dump(by_alias=True,
                                                     exclude_none=True))

    async with message_bus().topic("raw_activities").publish() as publish:
        await publish(event_type="Accept",
                      object_id=accept.id,
                      payload={"username": username,
                               "activity": accept.as_event_payload()},
                      message_id=_source_key.message_id(seq))

    logger.info("follow_handler: Accept published for %r", follow.actor)


async def _handle_undo_follow(username: str, activity: dict, seq: int) -> None:
    try:
        undo = UndoFollowActivity.model_validate(activity)
    except Exception:
        return

    async with message_bus().topic("followers").publish() as publish:
        await publish(event_type="deleted",
                      object_id=f"{undo.actor}|{actor_url_from_username(username)}",
                      payload={},
                      message_id=_source_key.message_id(seq))


async def handle_incoming_activities() -> None:
    async for seq, event_type, object_id, _, payload \
            in message_bus().topic("incoming_activities").subscribe():
        validated = incoming_activities["validate"](event_type, payload)
        if validated is not None:
            username = validated["username"]
            activity = {"id":   object_id,
                        "type": event_type,
                        **validated["activity"]}

        async def _unknown_type(u, a, s):
            pass

        await {"Follow": _handle_follow,
               "Undo": _handle_undo_follow}.get(event_type, _unknown_type)(username, activity, seq)

