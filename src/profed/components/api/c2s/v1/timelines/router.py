# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from fastapi import APIRouter, Depends, Query
from typing import Annotated, Optional
from profed.identity import actor_url_from_username, acct_from_username
from profed.components.api.c2s.v1.timelines.storage import storage
from profed.components.api.c2s.shared.auth import current_user 
 

router = APIRouter()
active = False
 

def init(config: dict) -> None:
    global active
    active = True 
 

def _activity_to_status(row_id: str, activity: dict) -> dict:
    obj = activity.get("object", {})
    if isinstance(obj, str):
        obj = {}
    actor_url      = activity.get("actor", "")
    actor_username = actor_url.rstrip("/").split("/")[-1]
    return {"id":                     row_id,
            "created_at":             obj.get("published", "1970-01-01T00:00:00.000Z"),
            "in_reply_to_id":         None,
            "in_reply_to_account_id": None,
            "sensitive":              False,
            "spoiler_text":           "",
            "visibility":             "public",
            "language":               None,
            "uri":                    activity.get("id", ""),
            "url":                    obj.get("url", activity.get("id", "")),
            "replies_count":          0,
            "reblogs_count":          0,
            "favourites_count":       0,
            "content":                obj.get("content", ""),
            "reblog":                 None,
            "application":            None,
            "account":                {"id":              actor_username,
                                       "username":        actor_username,
                                       "acct":            actor_url,
                                       "display_name":    actor_username,
                                       "locked":          False,
                                       "created_at":      "1970-01-01T00:00:00.000Z",
                                       "note":            "",
                                       "url":             actor_url,
                                       "avatar":          "",
                                       "avatar_static":   "",
                                       "header":          "",
                                       "header_static":   "",
                                       "followers_count": 0,
                                       "following_count": 0,
                                       "statuses_count":  0,
                                       "emojis":          [],
                                       "fields":          []},
            "media_attachments":      [],
            "mentions":               [],
            "tags":                   [],
            "emojis":                 [],
            "card":                   None,
            "poll":                   None}
 
 
@router.get("/timelines/home")
async def home_timeline(claims: Annotated[dict, Depends(current_user)],
                        limit: int = Query(default=20, ge=1, le=40),
                        max_id: Optional[str] = Query(default=None),
                        since_id: Optional[str] = Query(default=None)):
    username = claims.get("preferred_username") or claims.get("sub")
    store = await storage()
    rows = await store.fetch(username,
                             limit=limit,
                             max_id=max_id,
                             since_id=since_id)
    return [_activity_to_status(row_id, activity) for row_id, activity in rows]
