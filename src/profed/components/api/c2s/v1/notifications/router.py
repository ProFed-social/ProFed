# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from fastapi import APIRouter, Depends, HTTPException, Query
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


@router.get("/notifications/{id}")
async def get_notification(id: str,
                           claims: Annotated[dict, Depends(current_user)]):
    raise HTTPException(status_code=404, detail="notification_not_found")


@router.get("/push/subscription")
async def get_push_subscription(claims: Annotated[dict, Depends(current_user)]):
    raise HTTPException(status_code=404, detail="record_not_found")


@router.post("/push/subscription")
async def create_push_subscription(claims: Annotated[dict, Depends(current_user)]):
    raise HTTPException(status_code=422, detail="push_not_supported")


@router.delete("/push/subscription")
async def delete_push_subscription(claims: Annotated[dict, Depends(current_user)]):
    return {}

