# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import logging
from profed.core.message_bus import message_bus
from profed.core.message_bus.source_key import source_key
from profed.topics import incoming_activities
from profed.identity import actor_url_from_username
from profed.models.activity_pub import AcceptActivity
from .storage import storage
 
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
 
    account_id = await (await storage()).get_by_actor_url(accept.actor)
    if account_id is None:
        logger.warning("accept_handler: unknown actor %r", accept.actor)
        return

    async with message_bus().topic("known_accounts").publish() as publish:
        await publish(event_type="follow_accepted",
                      object_id=str(account_id),
                      payload={"following_user": username},
                      message_id=_source_key.message_id(seq))

    logger.info("accept_handler: follow_accepted for %r -> %r", username, accept.actor)
 

async def handle_incoming_activities() -> None:
    async for seq, event_type, object_id, _, payload in \
              message_bus().topic("incoming_activities").subscribe("accept_handler"):
        validated = incoming_activities["validate"](event_type, payload)
        if validated is None:
            continue

        username = validated["username"]
        activity = {"id":   object_id,
                    "type": event_type,
                    **validated["activity"]}

        try:
            if event_type == "Accept":
                await _handle_accept(username, activity, seq)
        except Exception:
            activity_type = activity.get("type")
            logger.exception("Error handling %s activity for %s", activity_type, username)

