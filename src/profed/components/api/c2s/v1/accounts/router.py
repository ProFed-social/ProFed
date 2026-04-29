# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from fastapi import APIRouter, Depends, HTTPException
from typing import Annotated
from profed.identity import actor_url_from_username, acct_from_username, account_id
from profed.components.api.c2s.shared.known_accounts.service import (lookup_by_id,
                                                                     lookup_by_acct,
                                                                     lookup_by_actor_url)
from profed.components.api.c2s.shared.actors.service import resolve_actor
from profed.components.api.c2s.shared.auth import current_user
from profed.core.message_bus import message_bus

 
router = APIRouter()
active = False
 

def init(config: dict) -> None:
    global active
    active = True

def _account_from_person(person, username: str) -> dict:
    return {"id":              account_id(acct_from_username(username)),
            "username":        username,
            "acct":            acct_from_username(username),
            "display_name":    person.name or username,
            "note":            person.summary or "",
            "url":             actor_url_from_username(username),
            "avatar":          None,
            "avatar_static":   None,
            "header":          None,
            "header_static":   None,
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
 
 
async def _resolve_account(id_or_acct: str, config: dict) -> dict | None:
    if id_or_acct.startswith("https://"):
        return await lookup_by_actor_url(id_or_acct, config)
    if "@" in id_or_acct:
        return await lookup_by_acct(id_or_acct, config)
    try:
        return await lookup_by_id(int(id_or_acct), config)
    except ValueError:
        return None
 
 
@router.post("/accounts/{id}/follow")
async def follow(id: str,
                 claims: Annotated[dict, Depends(current_user)]):
    username = claims.get("preferred_username") or claims.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="invalid_token")
 
    row = await _resolve_account(id, {})
    if row is None:
        raise HTTPException(status_code=404, detail="account_not_found")
 
    async with message_bus().topic("known_accounts").publish() as publish:
        await publish({"type":    "follow_requested",
                       "payload": {"account_id":    row["account_id"],
                                   "following_user": username}})
 
    actor_url = row["actor_url"]

    follow_id = f"{actor_url_from_username(username)}#follows/{row['account_id']}"
    async with message_bus().topic("activities").publish() as publish:
        await publish({"type":    "created",
                       "payload": {"id":       follow_id,
                                   "type":     "Follow",
                                   "actor":    actor_url_from_username(username),
                                   "object":   actor_url,
                                   "username": username}})
 
    return {"id":       str(row["account_id"]),
            "following": True,
            "requested": True}

