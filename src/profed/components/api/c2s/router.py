# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 

from typing import List
from fastapi import APIRouter
from profed.components.api.active_routers import narrow_deactivate_routers
from . import oauth, v1, v2
 
 
def mount_routers(parent, deactivate: List[str]) -> None:
    api = APIRouter(prefix="/api")
    v1.mount_routers(api, narrow_deactivate_routers("v1_", deactivate))
    v2.mount_routers(api, narrow_deactivate_routers("v2_", deactivate))
    parent.include_router(api)
    if "oauth" not in deactivate:
        oauth.mount_routers(parent, deactivate)

