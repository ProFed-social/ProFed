# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
from .storage import init as init_storage
from .projections import handle_events, rebuild
from .handler import handle_incoming_activities


using_schemata = ["accept_handler"]


async def AcceptHandler(config: dict) -> None:
    await init_storage(config)
    await rebuild()

    await asyncio.gather(handle_events(),
                         handle_incoming_activities())

