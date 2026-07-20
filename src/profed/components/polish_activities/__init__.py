# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import logging
from .storage import init as init_storage, storage as _storage
from .accounts_projection import accounts_handle_events, accounts_rebuild
from .translator import handle_events


logger = logging.getLogger(__name__)
using_schemata = ["polish_activities"]


async def PolishActivities(config: dict) -> None:
    await init_storage(config)
    await (await _storage()).ensure_schema()
    await accounts_rebuild()
    logger.info("polish_activities: accounts projection rebuilt, tailing")

    await asyncio.gather(accounts_handle_events(),
                         handle_events())

