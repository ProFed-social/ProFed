# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from fastapi import APIRouter, Depends, Query
from typing import Annotated
from profed.components.api.c2s.shared.auth import current_user


router = APIRouter()


active = False


def init(config: dict) -> None:
    global active
    active = True


@router.get("/suggestions")
async def get_suggestions(claims: Annotated[dict, Depends(current_user)],
                          limit: int = Query(default=40, ge=1, le=80)):
    return []

