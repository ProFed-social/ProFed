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


@router.get("/conversations")
async def get_conversations(claims: Annotated[dict, Depends(current_user)],
                            limit: int = Query(default=20, ge=1, le=40)):
    return []


@router.get("/filters")
async def get_filters(claims: Annotated[dict, Depends(current_user)]):
    return []


@router.post("/lists")
async def create_list(claims: Annotated[dict, Depends(current_user)]):
    raise HTTPException(status_code=422, detail="lists_not_supported")


@router.get("/lists/{id}")
async def get_list(id: str,
                   claims: Annotated[dict, Depends(current_user)] = None):
    raise HTTPException(status_code=404, detail="list_not_found")


@router.put("/lists/{id}")
async def update_list(id: str,
                      claims: Annotated[dict, Depends(current_user)]):
    raise HTTPException(status_code=404, detail="list_not_found")


@router.delete("/lists/{id}")
async def delete_list(id: str,
                      claims: Annotated[dict, Depends(current_user)]):
    raise HTTPException(status_code=404, detail="list_not_found")


@router.get("/lists/{id}/accounts")
async def get_list_accounts(id: str,
                            claims: Annotated[dict, Depends(current_user)] = None):
    raise HTTPException(status_code=404, detail="list_not_found")


@router.post("/lists/{id}/accounts")
async def add_list_accounts(id: str,
                            claims: Annotated[dict, Depends(current_user)]):
    raise HTTPException(status_code=404, detail="list_not_found")


@router.delete("/lists/{id}/accounts")
async def remove_list_accounts(id: str,
                              claims: Annotated[dict, Depends(current_user)]):
    raise HTTPException(status_code=404, detail="list_not_found")

