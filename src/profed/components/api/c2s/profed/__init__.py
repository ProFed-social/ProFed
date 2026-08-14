# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import List
from fastapi import APIRouter
from profed.components.api.http import MastodonJSONResponse
from profed.components.api.active_routers import get_active
from .timeline import router as timeline


async def init(config: dict, deactivate: List[str]) -> None:
    for r in get_active({"timeline": timeline}, deactivate):
        r.init(config)


def mount_routers(parent, deactivate: List[str]) -> None:
    router = APIRouter(prefix="/profed", default_response_class=MastodonJSONResponse)
    for r in get_active({"timeline": timeline}, deactivate):
        router.include_router(r.router)
    parent.include_router(router)

