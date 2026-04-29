# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from datetime import datetime, timezone, timedelta
from typing import Optional
from profed.core.message_bus import message_bus
from profed.federation.webfinger import lookup_acct, lookup_actor_url
from profed.http import http
from profed.identity import account_id as compute_account_id
from .storage import storage
 
WEBFINGER_CACHE_TTL = 86400  # 1 day default
 
 
async def _fetch_actor(actor_url: str) -> Optional[dict]:
    try:
        return await http("GET").json(
            actor_url,
            headers={"Accept": "application/activity+json"},
            timeout=10.0)
    except Exception:
        return None
 
 
async def _publish_discovered(account_id: int,
                              acct: str,
                              actor_url: str,
                              actor_data: dict) -> None:
    async with message_bus().topic("known_accounts").publish() as publish:
        await publish({"type": "discovered",
                       "payload": {"account_id": account_id,
                                   "acct": acct,
                                   "actor_url": actor_url,
                                   "actor_data": actor_data,
                                   "last_webfinger_at": 
                                        datetime.now(timezone.utc).isoformat()}})
 
 
async def _do_webfinger_lookup(acct: str) -> Optional[dict]:
    actor_url = await lookup_actor_url(acct)
    if actor_url is not None:
        actor_data = await _fetch_actor(actor_url)
        if actor_data is not None:
            aid = int(compute_account_id(acct))
            await _publish_discovered(aid, acct, actor_url, actor_data)
            return {"account_id": aid,
                    "acct":       acct,
                    "actor_url":  actor_url,
                    "actor_data": actor_data}
    return None
 
 
def _is_fresh(row: dict, ttl: int) -> bool:
    last = row["last_webfinger_at"]
    if isinstance(last, str):
        last = datetime.fromisoformat(last)
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - last < timedelta(seconds=ttl)
 
 
async def lookup_by_id(account_id: int,
                       config: dict | None = None) -> Optional[dict]:
    ttl = int((config or {}).get("webfinger_cache_ttl", WEBFINGER_CACHE_TTL))
    row = await (await storage()).get_by_id(account_id)
    if row is not None and _is_fresh(row, ttl):
        return row
    if row is not None:
        return await _do_webfinger_lookup(row["acct"]) or row
    return None
 
 
async def lookup_by_acct(acct: str,
                         config: dict | None = None) -> Optional[dict]:
    ttl = int((config or {}).get("webfinger_cache_ttl", WEBFINGER_CACHE_TTL))
    row = await (await storage()).get_by_acct(acct)
    if row is not None and _is_fresh(row, ttl):
        return row
    return await _do_webfinger_lookup(acct)
 
 
async def lookup_by_actor_url(actor_url: str,
                              config: dict | None = None) -> Optional[dict]:
    ttl = int((config or {}).get("webfinger_cache_ttl", WEBFINGER_CACHE_TTL))
    row = await (await storage()).get_by_actor_url(actor_url)
    if row is not None and _is_fresh(row, ttl):
        return row
    acct = await lookup_acct(actor_url)
    if acct is None:
        return row
    return await _do_webfinger_lookup(acct)
