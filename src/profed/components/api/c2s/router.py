# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from fastapi import APIRouter
from .apps      import router as apps
from .instance  import router as instance
from .accounts  import router as accounts
from .statuses  import router as statuses
from .timelines import router as timelines
 
 
def create_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1")
    for r in (apps, instance, accounts, statuses, timelines):
        if r.active:
            router.include_router(r.router)
    return router

