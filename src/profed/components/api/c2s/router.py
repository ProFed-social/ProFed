# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 

from typing import List
from fastapi import APIRouter
from profed.components.api.active_routers import narrow_deactivate_routers
from . import oauth, v1, v2
 
 
def create_router(deactivate: List[str]) -> APIRouter:
    api = APIRouter(prefix="/api")
    api.include_router(v1.create_router(narrow_deactivate_routers("v1_", deactivate)))
    api.include_router(v2.create_router(narrow_deactivate_routers("v2_", deactivate)))
    if "oauth" not in deactivate:
        api.include_router(oauth.create_router(deactivate))
    return api

