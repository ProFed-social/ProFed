# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import logging
from .storage import init as init_storage, storage as _storage
from .known_accounts_projection import known_accounts_handle_events, known_accounts_rebuild
from .instance_key import handle_events as instance_key_handle_events, rebuild as instance_key_rebuild
from .translator import handle_events


logger = logging.getLogger(__name__)
using_schemata = ["polish_activities"]


async def PolishActivities(config: dict) -> None:
    await init_storage(config)
    await (await _storage()).ensure_schema()
    await instance_key_rebuild()
    await known_accounts_rebuild()
    logger.info("polish_activities: projections rebuilt, tailing")

    await asyncio.gather(known_accounts_handle_events(),
                         instance_key_handle_events(),
                         handle_events())

