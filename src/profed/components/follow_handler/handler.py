# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import logging
 
from profed.core.message_bus import message_bus
from profed.core.message_bus.source_key import source_key
from profed.topics import incoming_activities
from profed.identity import actor_url_from_username, acct_from_username
from profed.models.activity_pub import (AcceptActivity,
                                        FollowActivity,
                                        UndoFollowActivity)
from profed.federation.webfinger import lookup_acct
 
 
logger = logging.getLogger(__name__)
_source_key = source_key("incoming_activities") 

 
async def _handle_follow(username: str, activity: dict, seq: int) -> None:
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
        await publish(event_type="created",
                      object_id=f"{follower_acct}|{following_acct}",
                      payload={},
                      message_id=_source_key.message_id(seq))

    logger.info("follow_handler: published follower %r -> %r", follower_acct, following_acct)
    accept = AcceptActivity(id=f"{follow.id}#accepts/",
                            actor=local_actor_url,
                            object=follow.model_dump(by_alias=True,
                                                     exclude_none=True))

    async with message_bus().topic("activities").publish() as publish:
        await publish(event_type="Accept",
                      object_id=accept.id,
                      payload={"username": username,
                               "activity": accept.as_event_payload()},
                      message_id=_source_key.message_id(seq))

    logger.info("follow_handler: Accept published for %r", follower_acct)
 
 
async def _handle_undo_follow(username: str, activity: dict, seq: int) -> None:
    try:
        undo = UndoFollowActivity.model_validate(activity)
    except Exception:
        return
 
    follower_acct = await lookup_acct(undo.actor)
    if follower_acct is None:
        logger.warning("WebFinger lookup failed for %s", undo.actor)
        return
 
    async with message_bus().topic("followers").publish() as publish:
        await publish(event_type="deleted",
                      object_id=f"{follower_acct}|{acct_from_username(username)}",
                      payload={},
                      message_id=_source_key.message_id(seq))


async def handle_incoming_activities() -> None:
    async for seq, event_type, object_id, _, payload \
            in message_bus().topic("incoming_activities").subscribe("follow_handler"):
        validated = incoming_activities["validate"](event_type, payload)
        if validated is None:
            logger.warning("follow_handler: ignoring invalid event: %r", event_type)
            continue

        username = validated["username"]
        activity = {"id":   object_id,
                    "type": event_type,
                    **validated["activity"]}

        async def _unknown_type(u, a, s):
            logger.debug(f"ignoring event in follow_handler: {event_type}")

        await {"Follow": _handle_follow,
               "Undo": _handle_undo_follow}.get(event_type, _unknown_type)(username, activity, seq)

