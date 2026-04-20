# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from profed.core.projections import build_projection
from profed.topics import followers, deliveries
from .storage import storage
 
 
async def _followers_init() -> None:
    store = await storage()
    await store.ensure_schema()
 
 
async def _follower_created(payload: dict) -> None:
    await (await storage()).add_follower(payload["following"], payload["follower"])
 
 
async def _follower_deleted(payload: dict) -> None:
    await (await storage()).remove_follower(payload["following"], payload["follower"])
 
 
followers_handle_events, followers_rebuild, _ = \
    build_projection(topic=followers,
                     subscriber="activity_delivery",
                     init=_followers_init,
                     on_snapshot_item=_follower_created,
                     on_message_type={"created": _follower_created,
                                      "deleted": _follower_deleted})
 
 
async def _deliveries_init() -> None:
    store = await storage()
    await store.ensure_schema()
 
 
async def _delivery_attempted(payload: dict) -> None:
    await (await storage()).upsert_delivery(payload)
 
 
deliveries_handle_events, deliveries_rebuild, _ = \
    build_projection(topic=deliveries,
                     subscriber="activity_delivery",
                     init=_deliveries_init,
                     on_snapshot_item=_delivery_attempted,
                     on_message_type={"attempted": _delivery_attempted})
 
 
async def get_followers(following: str) -> set[str]:
    return await (await storage()).get_followers(following)
 
 
async def get_delivery_status(activity_id: str, recipient: str) -> dict | None:
    return await (await storage()).get_delivery_status(activity_id, recipient)

