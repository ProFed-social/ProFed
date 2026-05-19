# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from fastapi import APIRouter, Depends, Query
from typing import Annotated, Optional
from profed.components.api.c2s.shared.auth import current_user


router = APIRouter()


active = False


def init(config: dict) -> None:
    global active
    active = True


@router.get("/markers")
async def get_markers(claims: Annotated[dict, Depends(current_user)],
                      timeline: Optional[list[str]] = Query(default=None)):
    return {}


@router.post("/markers")
async def save_markers(claims: Annotated[dict, Depends(current_user)]):
    return {}
