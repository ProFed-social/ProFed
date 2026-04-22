# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated
from profed.identity import actor_url_from_username, acct_from_username
from profed.components.api.c2s.shared.actors.service import resolve_actor
from profed.components.api.c2s.auth import current_user

 
router = APIRouter()
active = False
 

def init(config: dict) -> None:
    global active
    active = True

 
def _account_from_person(person, username: str) -> dict:
    return {"id":              username,
            "username":        username,
            "acct":            acct_from_username(username),
            "display_name":    person.name or username,
            "note":            person.summary or "",
            "url":             actor_url_from_username(username),
            "avatar":          "",
            "avatar_static":   "",
            "header":          "",
            "header_static":   "",
            "locked":          False,
            "bot":             False,
            "created_at":      "1970-01-01T00:00:00.000Z",
            "followers_count": 0,
            "following_count": 0,
            "statuses_count":  0,
            "emojis":          [],
            "fields":          [],
            "source":          {"privacy":   "public",
                                "sensitive": False,
                                "language":  None,
                                "note":      person.summary or "",
                                "fields":    []}}
 
 
@router.get("/accounts/verify_credentials")
async def verify_credentials(claims: Annotated[dict, Depends(current_user)]):
    username = claims.get("preferred_username") or claims.get("sub")

    if not username:
        raise HTTPException(status_code=401, detail="invalid_token")

    person = await resolve_actor(username)
    if person is None:
        raise HTTPException(status_code=404, detail="account_not_found")

    return _account_from_person(person, username)

