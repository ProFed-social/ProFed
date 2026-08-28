# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from profed.core.message_bus import message_bus
from profed.core.message_bus.source_key import source_key
from profed.topics import incoming_activities
from profed.identity import actor_url_from_username
from profed.models.activity_pub import AcceptActivity, RejectActivity

logger = logging.getLogger(__name__)
_source_key = source_key("incoming_activities")


async def _handle_accept(username: str, activity: dict, seq: int) -> None:
    try:
        accept = AcceptActivity.model_validate(activity)
    except Exception as e:
        logger.warning("Invalid Accept activity: %r – error: %s", activity, e)
        return

    follow_object = accept.object
    if not isinstance(follow_object, dict) or \
       follow_object.get("actor") != actor_url_from_username(username):
            return

    async with message_bus().topic("followers").publish() as publish:
        await publish(event_type="accepted",
                      object_id=f"{actor_url_from_username(username)}|{accept.actor}",
                      payload={},
                      message_id=_source_key.message_id(seq))

    logger.info("accept_handler: follow_accepted for %r -> %r", username, accept.actor)


async def _handle_reject(username: str, activity: dict, seq: int) -> None:
    try:
        reject = RejectActivity.model_validate(activity)
    except Exception as e:
        logger.warning("Invalid Reject activity: %r – error: %s", activity, e)
        return

    follow_object = reject.object
    if not isinstance(follow_object, dict) or \
       follow_object.get("actor") != actor_url_from_username(username):
            return

    async with message_bus().topic("followers").publish() as publish:
        await publish(event_type="rejected",
                      object_id=f"{actor_url_from_username(username)}|{reject.actor}",
                      payload={},
                      message_id=_source_key.message_id(seq))


async def handle_incoming_activities() -> None:
    async for seq, event_type, object_id, _, payload in \
              message_bus().topic("incoming_activities").subscribe():
        validated = incoming_activities["validate"](event_type, payload)
        if validated is None:
            continue

        username = validated["username"]
        activity = {"id":   object_id,
                    "type": event_type,
                    **validated["activity"]}

        try:
            async def _ignore(u, a, s):
                pass
            await {"Accept": _handle_accept,
                   "Reject": _handle_reject}.get(event_type,
                                                 _ignore)(username,
                                                          activity,
                                                          seq)
        except Exception:
            activity_type = activity.get("type")
            logger.exception("Error handling %s activity for %s", activity_type, username)

