# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import logging
 
from profed.core.message_bus import message_bus
from profed.topics import incoming_activities
from profed.identity import actor_url_from_username, acct_from_username
from profed.models.activity_pub import (AcceptActivity,
                                        FollowActivity,
                                        UndoFollowActivity)
from .webfinger import lookup_acct
 
 
logger = logging.getLogger(__name__)
 
 
async def _handle_follow(username: str, activity: dict) -> None:
    try:
        follow = FollowActivity.model_validate(activity)
    except Exception as e:
        logger.warning("Invalid Follow activity: %r – error: %s", activity, e)
        return

    following_acct = acct_from_username(username)
    local_actor_url = actor_url_from_username(username)
 
    follower_acct = await lookup_acct(follow.actor)
    if follower_acct is None:
        logger.warning("follow_handler: WebFinger lookup returned None for %r", follow.actor)
        return
    logger.info("follow_handler: WebFinger resolved %r -> %r", follow.actor, follower_acct)

    async with message_bus().topic("followers").publish() as publish:
            await publish({"type": "created",
                       "payload": {"follower": follower_acct,
                                   "following": following_acct}})
 
    logger.info("follow_handler: published follower %r -> %r", follower_acct, following_acct)
    accept = AcceptActivity(id=f"{follow.id}#accepts/",
                            actor=local_actor_url,
                            object=follow.model_dump(by_alias=True,
                                                     exclude_none=True))

    async with message_bus().topic("activities").publish() as publish:
        await publish({"type": "created",
                       "payload": {"username": username,
                                   **accept.model_dump(by_alias=True,
                                                       exclude_none=True)}})
    logger.info("follow_handler: Accept published for %r", follower_acct)
 
 
async def _handle_undo_follow(username: str, activity: dict) -> None:
    try:
        undo = UndoFollowActivity.model_validate(activity)
    except Exception:
        return
 
    follower_acct = await lookup_acct(undo.actor)
    if follower_acct is None:
        logger.warning("WebFinger lookup failed for %s", undo.actor)
        return
 
    async with message_bus().topic("followers").publish() as publish:
        await publish({"type": "deleted",
                       "payload": {"follower": follower_acct,
                                   "following": acct_from_username(username)}})


async def handle_incoming_activities() -> None:
    async for event in message_bus().topic("incoming_activities").subscribe("follow_handler", 0):
        event_type, payload = incoming_activities["validate"](event)
        if event_type is None:
            logger.warning("follow_handler: ignoring invalid event: %r", event)
            continue
 
        activity = payload["activity"]
        username = payload["username"]
        activity_type = activity.get("type")
 
        try:
            if activity_type == "Follow":
                logger.info("follow_handler: handling Follow from %r to %r", activity.get("actor"), username) 
                await _handle_follow(username, activity)
            elif activity_type == "Undo":
                await _handle_undo_follow(username, activity)
        except Exception:
            logger.exception("Error handling %s activity for %s", activity_type, username)

