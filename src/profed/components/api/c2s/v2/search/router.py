# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from fastapi import APIRouter, Depends
from typing import Annotated, Optional
from profed.components.api.c2s.shared.auth import current_user
from profed.components.api.c2s.shared.search.resolvers import resolve_search
 
router = APIRouter()
active = False
 
 
def init(config: dict) -> None:
    global active
    active = True
 
 
@router.get("/search")
async def search(q:       str,
                 type:    Optional[str] = None,
                 resolve: bool          = False,
                 limit:   int           = 20,
                 _user:   Annotated[dict, Depends(current_user)] = None):
    return await resolve_search(q, type=type, resolve=resolve, limit=limit)

