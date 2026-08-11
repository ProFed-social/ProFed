# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Annotated, Optional
from profed.components.api.c2s.shared.statuses import user_timeline, service
from profed.components.api.c2s.shared.auth import current_user


router = APIRouter()
active = False


def init(config: dict) -> None:
    global active
    active = True


@router.get("/timelines/home")
async def home_timeline(claims: Annotated[dict, Depends(current_user)],
                        limit: int = Query(default=20, ge=1, le=40),
                        max_id: Optional[str] = Query(default=None),
                        since_id: Optional[str] = Query(default=None)):
    rows = await (await user_timeline.storage()).fetch(claims.get("preferred_username") or claims.get("sub"),
                                                       limit=limit,
                                                       max_id=max_id,
                                                       since_id=since_id)
    return await service.make_statuses(rows)


@router.get("/timelines/public")
async def public_timeline(claims: Annotated[dict, Depends(current_user)],
                          limit: int = Query(default=20, ge=1, le=40),
                          max_id: Optional[str] = Query(default=None),
                          since_id: Optional[str] = Query(default=None),
                          local: bool = Query(default=False)):
    return []


@router.get("/timelines/tag/{hashtag}")
async def hashtag_timeline(hashtag: str,
                           claims: Annotated[dict, Depends(current_user)],
                           limit: int = Query(default=20, ge=1, le=40),
                           max_id: Optional[str] = Query(default=None),
                           since_id: Optional[str] = Query(default=None),
                           local: bool = Query(default=False)):
    return []


@router.get("/timelines/list/{list_id}")
async def list_timeline(list_id: str,
                        claims: Annotated[dict, Depends(current_user)],
                        limit: int = Query(default=20, ge=1, le=40),
                        max_id: Optional[str] = Query(default=None),
                        since_id: Optional[str] = Query(default=None)):
    raise HTTPException(status_code=404, detail="list_not_found")

