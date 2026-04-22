# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from . import projection, service, router

from typing import List
from fastapi import APIRouter
import asyncio
 
 
async def init(config: dict) -> None:
    await projection.apps_rebuild()
    await projection.codes_rebuild()
    router.init(config)
    asyncio.create_task(projection.apps_handle_events(),  name="c2s_oauth_apps")
    asyncio.create_task(projection.codes_handle_events(), name="c2s_oauth_codes")
 
 
def mount_routers(parent, deactivate: List[str]) -> None:
    parent.include_router(router.router)

