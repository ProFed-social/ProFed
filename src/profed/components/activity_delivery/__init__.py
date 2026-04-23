# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import logging
import asyncio
from .storage import init as init_storage
from .projections import (followers_handle_events,
                           followers_rebuild,
                           deliveries_handle_events,
                           deliveries_rebuild,
                           keys_handle_events,
                           keys_rebuild)
from .handler import handle_activities


logger = logging.getLogger(__name__)
 
 
async def ActivityDelivery(config: dict) -> None:
    await asyncio.sleep(5)
    logger.info("setting up activity delivery")
    await init_storage(config)
    logger.info("storage has been initialized")
    await asyncio.gather(followers_rebuild(),
                         deliveries_rebuild(),
                         keys_rebuild())
    logger.info("projections have been rebuilt")

    asyncio.create_task(followers_handle_events(), name="activity_delivery_followers")
    logger.info("kicked off follwers handler")
    asyncio.create_task(deliveries_handle_events(), name="activity_delivery_deliveries")
    logger.info("kicked off deliveries handler")
    asyncio.create_task(keys_handle_events(), name="activity_delivery_keys")
    logger.info("kicked off keys handler")
    asyncio.create_task(handle_activities(config), name="activity_delivery_handler")
    logger.info("kicked off activities handler")

