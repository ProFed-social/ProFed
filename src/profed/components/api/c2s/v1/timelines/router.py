# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Annotated, Optional
from profed.identity import actor_url_from_username, acct_from_username
from profed.components.api.c2s.v1.timelines.storage import storage
from profed.components.api.c2s.shared.known_accounts.service import lookup_multiple
from profed.models.mastodon import Account, Status
from profed.components.api.c2s.shared.auth import current_user 
 

router = APIRouter()
active = False
 

def init(config: dict) -> None:
    global active
    active = True 
 

def _activity_to_status(row_id: str,
                        activity: dict,
                        accounts: dict[str, Account]) -> Status:
    obj = activity.get("object", {})
    if isinstance(obj, str):
        obj = {}
    actor_url      = activity.get("actor", "")
    username = actor_url.rstrip("/").split("/")[-1]

    return Status(id=          row_id,
                  created_at=  obj.get("published", "1970-01-01T00:00:00.000Z"),
                  uri=         activity.get("id", ""),
                  url=         obj.get("url", activity.get("id", "")),
                  content=     obj.get("content", ""),
                  account=     accounts.get(actor_url, Account(id=           "0",
                                                               username=     username,
                                                               acct=         actor_url,
                                                               display_name= username,
                                                               url=          actor_url)))
 
 
@router.get("/timelines/home")
async def home_timeline(claims: Annotated[dict, Depends(current_user)],
                        limit: int = Query(default=20, ge=1, le=40),
                        max_id: Optional[str] = Query(default=None),
                        since_id: Optional[str] = Query(default=None)):
    rows = await (await storage()).fetch(claims.get("preferred_username") or claims.get("sub"),
                                         limit=limit,
                                         max_id=max_id,
                                         since_id=since_id)
    accounts   = await lookup_multiple(list({activity.get("actor", "")
                                             for _, activity in rows}))
    return [_activity_to_status(row_id, activity, accounts) for row_id, activity in rows]


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

