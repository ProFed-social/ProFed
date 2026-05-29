# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from profed.core.persistence.projections import build_projection, with_event_type
from profed.topics import followers, deliveries, users
from .storage import storage
 
 
async def _followers_init() -> None:
    pass
 
 
async def _follower_created(object_id: str, payload: dict) -> None:
    follower, following = object_id.split("|", 1)
    await (await storage()).add_follower(following, follower)


async def _follower_deleted(object_id: str, payload: dict) -> None:
    follower, following = object_id.split("|", 1)
    await (await storage()).remove_follower(following, follower)


async def _follower_snapshot(item: dict) -> None:
    await (await storage()).add_follower(item["following"], item["follower"])
 
 
followers_handle_events, followers_rebuild, _ = \
    build_projection(topic=followers,
                     subscriber="activity_delivery",
                     init=_followers_init,
                     on_snapshot_item=_follower_snapshot,
                     on_message_type={"created": _follower_created,
                                      "deleted": _follower_deleted})
 
 
async def _deliveries_init() -> None:
    pass
 
 
async def _delivery_event(event_type: str,
                          object_id:  str,
                          payload:    dict) -> None:
    activity_id, recipient = object_id.split("|", 1)
    await (await storage()).upsert_delivery({"activity_id": activity_id,
                                             "recipient": recipient,
                                             "success": event_type == "delivery_succeeded",
                                             "attempt": payload["attempt"],
                                             "status_code": payload.get("status_code"),
                                             "retry_after": payload.get("retry_after"),
                                             "first_attempt_at": payload["first_attempt_at"]})


async def _delivery_snapshot(item: dict) -> None:
    await (await storage()).upsert_delivery(item) 


deliveries_handle_events, deliveries_rebuild, _ = \
    build_projection(topic=deliveries,
                     subscriber="activity_delivery",
                     init=_deliveries_init,
                     on_snapshot_item=_delivery_snapshot,
                     on_message_type={"delivery_succeeded": _delivery_event,
                                      "delivery_failed": _delivery_event,
                                      "delivery_gave_up": _delivery_event},
                     event_handler_signature=with_event_type)
 
 
async def _keys_init() -> None:
    pass
 
 
async def _upsert_key(object_id: str, payload: dict) -> None:
    if "public_key_pem" not in payload or "private_key_pem" not in payload:
        return
    await (await storage()).upsert_user_key(object_id,
                                            payload["public_key_pem"],
                                            payload["private_key_pem"])


async def _upsert_key_snapshot(item: dict) -> None:
    if "public_key_pem" not in item or "private_key_pem" not in item:
        return
    await (await storage()).upsert_user_key(item["username"],
                                            item["public_key_pem"],
                                            item["private_key_pem"])
 
 
keys_handle_events, keys_rebuild, _ = \
    build_projection(topic=users,
                     subscriber="activity_delivery_keys",
                     init=_keys_init,
                     on_snapshot_item=_upsert_key_snapshot,
                     on_message_type={"created":        _upsert_key,
                                      "keys_generated": _upsert_key})

 
async def get_followers(following: str) -> set[str]:
    return await (await storage()).get_followers(following)
 
 
async def get_delivery_status(activity_id: str, recipient: str) -> dict | None:
    return await (await storage()).get_delivery_status(activity_id, recipient)

