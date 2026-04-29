# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import asyncio
from .storage import init as init_storage
from .projections import handle_events, rebuild
from .handler import handle_incoming_activities
 
 
async def AcceptHandler(config: dict) -> None:
    await init_storage(config)
    await rebuild()
    asyncio.create_task(handle_events(), name="accept_handler_projection")
    asyncio.create_task(handle_incoming_activities(), name="accept_handler")

