# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from typing import List
from fastapi import APIRouter
from profed.components.api.active_routers import get_active
from .instance import router as instance
from .search import router as search
from .suggestions import router as suggestions
from .filters import router as filters
from .media import router as media
 
 
async def init(config: dict, deactivate: List[str]) -> None:
    for r in get_active({"instance": instance,
                         "search": search,
                         "suggestions": suggestions,
                         "filters": filters,
                         "media": media},
                        deactivate):
        r.init(config)


def mount_routers(parent, deactivate: List[str]) -> None:
    router = APIRouter(prefix="/v2")
    for r in get_active({"instance": instance,
                         "search": search,
                         "suggestions": suggestions,
                         "filters": filters,
                         "media": media},
                        deactivate):
        if r.active:
            router.include_router(r.router)
    parent.include_router(router)

