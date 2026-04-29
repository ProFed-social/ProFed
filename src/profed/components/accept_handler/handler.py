# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import logging
from profed.core.message_bus import message_bus
from profed.topics import incoming_activities
from profed.identity import actor_url_from_username
from profed.models.activity_pub import AcceptActivity
from .storage import storage
 
logger = logging.getLogger(__name__)
 
 
async def _handle_accept(username: str, activity: dict) -> None:
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
        await publish({"type":    "follow_accepted",
                       "payload": {"account_id": account_id,
                                   "following_user": username}})
    logger.info("accept_handler: follow_accepted for %r -> %r",
                username,
                accept.actor)
 
 
async def handle_incoming_activities() -> None:
    async for event in message_bus().topic("incoming_activities").subscribe("accept_handler", 0):
        event_type, payload = incoming_activities["validate"](event)
        if event_type is None:
            logger.warning("accept_handler: ignoring invalid event: %r", event)
            continue
 
        activity      = payload["activity"]
        username      = payload["username"]
        activity_type = activity.get("type")
 
        try:
            if activity_type == "Accept":
                logger.info("accept_handler: handling Accept for %r", username)
                await _handle_accept(username, activity)
        except Exception:
            logger.exception("Error handling %s activity for %s",
                             activity_type,
                             username)

