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


@router.get("/notifications")
async def list_notifications(claims: Annotated[dict, Depends(current_user)],
                             limit: int = Query(default=20, ge=1, le=40),
                             max_id: Optional[str] = Query(default=None),
                             since_id: Optional[str] = Query(default=None),
                             types: Optional[list[str]] = Query(default=None),
                             exclude_types: Optional[list[str]] = Query(default=None),
                             account_id: Optional[str] = Query(default=None)):
    return []


@router.post("/notifications/clear")
async def clear_notifications(claims: Annotated[dict, Depends(current_user)]):
    return {}


@router.post("/notifications/{id}/dismiss")
async def dismiss_notification(id: str,
                              claims: Annotated[dict, Depends(current_user)]):
    return {}

