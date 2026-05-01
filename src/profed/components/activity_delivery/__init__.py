# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import asyncio
from .storage import init as init_storage
from .projections import (followers_handle_events,
                          followers_rebuild,
                          deliveries_handle_events,
                          deliveries_rebuild,
                          keys_handle_events,
                          keys_rebuild)
from .handler import handle_activities
 
 
async def ActivityDelivery(config: dict) -> None:
    await init_storage(config)
    await (await storage.storage()).ensure_schema()
    await asyncio.gather(followers_rebuild(),
                         deliveries_rebuild(),
                         keys_rebuild())

    asyncio.create_task(followers_handle_events(), name="activity_delivery_followers")
    asyncio.create_task(deliveries_handle_events(), name="activity_delivery_deliveries")
    asyncio.create_task(keys_handle_events(), name="activity_delivery_keys")
    asyncio.create_task(handle_activities(config), name="activity_delivery_handler")

