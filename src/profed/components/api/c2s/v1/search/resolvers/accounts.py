# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import logging
from typing import Optional
from profed.federation.webfinger import lookup_actor_url
from profed.identity import account_id
from profed.http.client import http 

logger = logging.getLogger(__name__)
 
 
async def _fetch_actor(actor_url: str) -> Optional[dict]:
    try:
        return await http("GET").json(actor_url,
                                       headers={"Accept": "application/activity+json"},
                                       timeout=10.0)
    except Exception:
        logger.warning("Failed to fetch actor %s", actor_url)
        return None 
 
def _actor_to_account(actor: dict, acct: str) -> dict:
    username, _ = acct.split("@", 1)
    return {"id":              account_id(acct),
            "username":        username,
            "acct":            acct,
            "display_name":    actor.get("name") or username,
            "note":            actor.get("summary") or "",
            "url":             actor.get("url") or actor.get("id", ""),
            "avatar":          "",
            "header":          "",
            "followers_count": 0,
            "following_count": 0,
            "statuses_count":  0,
            "emojis":          [],
            "fields":          []}
 
 
async def resolve(q: str, resolve: bool = False, limit: int = 20) -> dict:
    if "@" not in q or not resolve:
        return {}

    acct = q.lstrip("@")
    actor_url = await lookup_actor_url(acct)
    if actor_url is not None:
        actor = await _fetch_actor(actor_url)
        if actor is not None:
            return {"accounts": [_actor_to_account(actor, acct)]}

    return {}
