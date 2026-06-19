# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional
from profed.federation.webfinger import lookup_acct, lookup_actor_url
from profed.federation.actors import fetch_and_register_actor
from profed.identity import domain
from .storage import storage
from profed.models.mastodon import Account

 
WEBFINGER_CACHE_TTL = 86400

 
async def _do_webfinger_lookup(acct: str) -> Optional[dict]:
    actor_url = await lookup_actor_url(acct)
    actor_data = await fetch_and_register_actor(actor_url) if actor_url is not None else None
    if actor_data is None:
        return None

    return Account.from_actor(actor_data, acct=acct, url=actor_url)
 
 
def _is_fresh(row: dict, ttl: int) -> bool:
    if (row.get("acct") or "").endswith("@" + domain()):
        return True

    last = row["last_webfinger_at"]
    if isinstance(last, str):
        last = datetime.fromisoformat(last)
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)

    return datetime.now(timezone.utc) - last < timedelta(seconds=ttl)


def _ttl(config: dict | None) -> int:
    return int(((config or {}).get("webfinger_cache_ttl", WEBFINGER_CACHE_TTL)
                if config is not None else
                WEBFINGER_CACHE_TTL)) 


def _account_from_row(row: dict) -> Account:
    return Account.model_validate(row["account"]) 


async def lookup_by_id(account_id: int,
                       config: dict | None = None) -> Optional[Account]:
    row = await (await storage()).get_by_id(account_id)

    return (None
            if row is None else
            _account_from_row(row)
            if _is_fresh(row, _ttl(config)) else
            await _do_webfinger_lookup(row["acct"]) or _account_from_row(row))
 
 
async def lookup_by_acct(acct: str,
                         config: dict | None = None) -> Optional[Account]:
    row = await (await storage()).get_by_acct(acct)
    return (_account_from_row(row)
            if row is not None and _is_fresh(row, _ttl(config)) else 
            await _do_webfinger_lookup(acct))
 

async def lookup_by_actor_url(actor_url: str,
                              config: dict | None = None) -> Optional[Account]:
    row = await (await storage()).get_by_actor_url(actor_url)
    if row is not None and _is_fresh(row, _ttl(config)):
       return _account_from_row(row)

    acct = await lookup_acct(actor_url)
    return (await _do_webfinger_lookup(acct)
            if acct is not None else
            _account_from_row(row)
            if row is not None else
            None)


async def lookup_multiple(actor_urls: list[str],
                          config: dict | None = None) -> dict[str, Account]:
    return {u: a
            for u, a in zip(actor_urls,
                            await asyncio.gather(*(lookup_by_actor_url(u, config)
                                                   for u in actor_urls)))
            if a is not None}

