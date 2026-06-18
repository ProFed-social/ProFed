# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional
from profed.federation.webfinger import lookup_acct, lookup_actor_url
from profed.federation.actors import fetch_and_register_actor
from profed.identity import account_id as compute_account_id, domain
from .storage import storage
from profed.models.mastodon import Account

 
WEBFINGER_CACHE_TTL = 86400

 
async def _do_webfinger_lookup(acct: str) -> Optional[dict]:
    actor_url = await lookup_actor_url(acct)
    actor_data = await fetch_and_register_actor(actor_url) if actor_url is not None else None
    if actor_data is None:
        return None

    return {"account_id": int(compute_account_id(acct)),
            "acct": acct,
            "actor_url": actor_url,
            "actor_data": actor_data}
 
 
def _is_fresh(row: dict, ttl: int) -> bool:
    if (row.get("acct") or "").endswith("@" + domain()):
        return True

    last = row["last_webfinger_at"]
    if isinstance(last, str):
        last = datetime.fromisoformat(last)
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)

    return datetime.now(timezone.utc) - last < timedelta(seconds=ttl)


def _ttl(config):
    return int((config or {}).get("webfinger_cache_ttl", WEBFINGER_CACHE_TTL))

 
async def lookup_by_id(account_id: int,
                       config: dict | None = None) -> Optional[Account]:
    row = await (await storage()).get_by_id(account_id)
    return (make_account(row
                         if _is_fresh(row, _ttl(config)) else
                         await _do_webfinger_lookup(row["acct"]) or row)
            if row is not None else
            None)
 
 
async def lookup_by_acct(acct: str,
                         config: dict | None = None) -> Optional[Account]:
    row = await (await storage()).get_by_acct(acct)
    raw = (row
           if row is not None and _is_fresh(row, _ttl(config)) else
           await _do_webfinger_lookup(acct))
    return make_account(raw) if raw is not None else None 

 
async def lookup_by_actor_url(actor_url: str,
                              config: dict | None = None) -> Optional[Account]:
    row = await (await storage()).get_by_actor_url(actor_url)
    if row is not None and _is_fresh(row, _ttl(config)):
        return make_account(row)

    acct = await lookup_acct(actor_url)
    raw = row if acct is None else await _do_webfinger_lookup(acct)
    return make_account(raw) if raw is not None else None


async def lookup_multiple(actor_urls: list[str],
                          config: dict | None = None) -> dict[str, Account]:
    return {u: a
            for u, a in zip(actor_urls,
                            await asyncio.gather(*(lookup_by_actor_url(u, config)
                                                   for u in actor_urls)))
            if a is not None}


def make_account(raw: dict) -> Account:
    return Account.from_actor(raw.get("actor_data") or {},
                              acct=raw["acct"],
                              url=raw["actor_url"],
                              created_at=raw.get("created_at"))

