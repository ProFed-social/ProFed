# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import logging
from .storage import (init as init_storage,
                      storage as _storage)
from .projections import followers_handle_events, followers_rebuild
from .translator import handle_events as activities_handle_events, rebuild as activities_rebuild


logger = logging.getLogger(__name__)
using_schemata = ["delivery_splitter"]


async def DeliverySplitter(config: dict) -> None:
    await init_storage(config)
    await (await _storage()).ensure_schema()
    logger.info("delivery_splitter: schema ready, rebuilding follower history")
    await followers_rebuild()
    logger.info("delivery_splitter: follower history rebuilt, rebuilding activities")
    asyncio.create_task(followers_handle_events(), name="delivery_splitter_followers")
    await activities_rebuild()
    logger.info("delivery_splitter: activities rebuilt, now tailing live")
    await activities_handle_events()

