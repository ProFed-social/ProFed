# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
from .storage import (init as init_storage,
                      storage as _storage)
from .projections import followers_handle_events, followers_rebuild
from .translator import handle_events as activities_handle_events, rebuild as activities_rebuild


using_schemata = ["delivery_splitter"]


async def DeliverySplitter(config: dict) -> None:
    await init_storage(config)
    await (await _storage()).ensure_schema()
    await followers_rebuild()
    asyncio.create_task(followers_handle_events(), name="delivery_splitter_followers")
    await activities_rebuild()
    await activities_handle_events()

