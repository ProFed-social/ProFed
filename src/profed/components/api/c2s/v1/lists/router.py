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


@router.get("/lists")
async def get_lists(claims: Annotated[dict, Depends(current_user)]):
    return []


@router.get("/bookmarks")
async def get_bookmarks(claims: Annotated[dict, Depends(current_user)],
                        limit: int = Query(default=20, ge=1, le=40),
                        max_id: Optional[str] = Query(default=None),
                        since_id: Optional[str] = Query(default=None)):
    return []


@router.get("/favourites")
async def get_favourites(claims: Annotated[dict, Depends(current_user)],
                         limit: int = Query(default=20, ge=1, le=40),
                         max_id: Optional[str] = Query(default=None),
                         since_id: Optional[str] = Query(default=None)):
    return []

