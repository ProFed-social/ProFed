# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from profed.identity import actor_url_from_username, acct_from_username, account_id
from profed.components.api.c2s.shared.known_accounts.service import (lookup_by_id,
                                                                     lookup_by_acct,
                                                                     lookup_by_actor_url)
from profed.components.api.c2s.shared.actors.service import resolve_actor
from profed.components.api.c2s.shared.auth import current_user
from profed.core.message_bus import message_bus
from profed.components.api.c2s.v1.accounts.following.storage import storage as following_storage
 
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
 
 
@router.get("/accounts/relationships")
async def relationships(id: list[str] = Query(default=[], alias="id[]"),
                        claims: Annotated[dict, Depends(current_user)] = None):
    username = claims.get("preferred_username") or claims.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="invalid_token")

    async def _resolve_account_id(query):
        row = await _resolve_account(query, {})
        if row is not None:
            return row["account_id"]
        return None

    resolved = {query: account_id
                for query, account_id in ((q, int(q)
                                              if q.isdigit() else
                                              await _resolve_account_id(q))
                                          for q in id)
                if account_id is not None}

    rows = await (await following_storage()).get_following(username, filter=list(resolved.values()))
    following_map = {row["account_id"]: row for row in rows}
    return [{"id":              str(resolved[query]),
             "following":       following_map.get(resolved[query], {}).get("accepted", False),
             "requested":       (resolved[query] in following_map and
                                 not following_map[resolved[query]]["accepted"]),
             "followed_by":     False,
             "blocking":        False,
             "muting":          False,
             "domain_blocking": False,
             "endorsed":        False,
             "note":            ""} for query in id if query in resolved]


async def _resolve_account(query: str, config: dict) -> dict | None:
    domain = config.get("domain", "")
    return (await lookup_by_actor_url(query, config)
            if query.startswith("https://") else
            await lookup_by_id(int(query), config)
            if query.isdigit() else
            await lookup_by_acct(f"{query}@{domain}" if "@" not in query else query, config)
            or (await lookup_by_acct(query, config) if "@" not in query else None))

 
@router.post("/accounts/{id}/follow")
async def follow(id: str,
                 claims: Annotated[dict, Depends(current_user)]):
    username = claims.get("preferred_username") or claims.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="invalid_token")
 
    row = await _resolve_account(id, {})
    if row is None:
        raise HTTPException(status_code=404, detail="account_not_found")
 
    actor_url = row["actor_url"]
    follow_id = f"{actor_url_from_username(username)}#follows/{uuid.uuid4()}"

    async with message_bus().topic("known_accounts").publish() as publish:
        await publish({"type":    "follow_requested",
                       "payload": {"account_id":    row["account_id"],
                                   "following_user": username,
                                   "follow_activity_id": follow_id}})
 
    async with message_bus().topic("activities").publish() as publish:
        await publish({"type":    "created",
                       "payload": {"id":       follow_id,
                                   "type":     "Follow",
                                   "actor":    actor_url_from_username(username),
                                   "object":   actor_url,
                                   "username": username}})
 
    return {"id":       str(row["account_id"]),
            "following": False,
            "requested": True}


@router.get("/accounts/familiar_followers")
async def familiar_followers(id: list[str] = Query(default=[], alias="id[]"),
                             claims: Annotated[dict, Depends(current_user)] = None):
    return []


@router.get("/accounts/{id}/featured_tags")
async def featured_tags(id: str):
    return []


@router.get("/accounts/{id}/statuses")
async def account_statuses(id: str,
                           claims: Annotated[dict, Depends(current_user)] = None):
    return []


@router.post("/accounts/{id}/unfollow")
async def unfollow(id: str,
                   claims: Annotated[dict, Depends(current_user)]):
    username = claims.get("preferred_username") or claims.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="invalid_token")

    account = await _resolve_account(id, {})
    if account is None:
        raise HTTPException(status_code=404, detail="account_not_found")

    following = await (await following_storage()).get(account["account_id"], username)
    follow_id = ((following or {}).get("follow_activity_id")
                 or f"{actor_url_from_username(username)}#follows/{account['account_id']}")
    actor_url  = actor_url_from_username(username)
    undo_id    = f"{actor_url}#unfollows/{uuid.uuid4()}"

    async with message_bus().topic("known_accounts").publish() as publish:
        await publish({"type": "unfollow",
                       "payload": {"account_id": account["account_id"],
                                   "following_user": username}})

    async with message_bus().topic("activities").publish() as publish:
        await publish({"type":    "created",
                       "payload": {"id":       undo_id,
                                   "type":     "Undo",
                                   "actor":    actor_url,
                                   "object":   {"id":     follow_id,
                                                "type":   "Follow",
                                                "actor":  actor_url,
                                                "object": account["actor_url"]},
                                   "username": username}})

    return {"id": str(account["account_id"]),
            "following": False,
            "requested": False}

