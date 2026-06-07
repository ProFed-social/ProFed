# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional
from profed.core.message_bus import message_bus
from profed.federation.webfinger import lookup_acct, lookup_actor_url
from profed.federation.actors import fetch_actor
from profed.identity import account_id as compute_account_id, domain
from .storage import storage
from profed.models.mastodon import Account

 
WEBFINGER_CACHE_TTL = 86400  # 1 day default
 
async def _publish_discovered(account_id: int,
                              acct: str,
                              actor_url: str,
                              actor_data: dict) -> None:
    async with message_bus().topic("known_accounts").publish() as publish:
        await publish(event_type="discovered",
                      object_id=str(account_id),
                      payload={"acct": acct,
                               "actor_url": actor_url,
                               "actor_data":  actor_data,
                               "last_webfinger_at": datetime.now(timezone.utc).isoformat()}) 

 
async def _do_webfinger_lookup(acct: str) -> Optional[dict]:
    actor_url = await lookup_actor_url(acct)
    actor_data = await fetch_actor(actor_url) if actor_url is not None else None
    if actor_data is None:
        return None

    aid = int(compute_account_id(acct))
    await _publish_discovered(aid, acct, actor_url, actor_data)
    return {"account_id": aid,
            "acct":       acct,
            "actor_url":  actor_url,
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
                       config: dict | None = None) -> Optional[dict]:
    row = await (await storage()).get_by_id(account_id)
    if row is not None:
        return (row
                if _is_fresh(row, _ttl(config)) else
                await _do_webfinger_lookup(row["acct"]) or row)
    return None
 
 
async def lookup_by_acct(acct: str,
                         config: dict | None = None) -> Optional[dict]:
    row = await (await storage()).get_by_acct(acct)
    return (row
            if row is not None and _is_fresh(row, _ttl(config)) else
            await _do_webfinger_lookup(acct))
 
 
async def lookup_by_actor_url(actor_url: str,
                              config: dict | None = None) -> Optional[dict]:
    row = await (await storage()).get_by_actor_url(actor_url)
    if row is not None and _is_fresh(row, _ttl(config)):
        return row

    acct = await lookup_acct(actor_url)
    return row if acct is None else await _do_webfinger_lookup(acct)



async def lookup_multiple(actor_urls: list[str],
                          config: dict | None = None) -> dict[str, Account]:
    raws = await asyncio.gather(*(lookup_by_actor_url(url, config) for url in actor_urls))
    return {url: make_account(raw)
            for url, raw in zip(actor_urls, raws)
            if raw is not None}


def make_account(raw: dict) -> Account:
    actor_data = raw.get("actor_data") or {}
    username = raw["acct"].split("@")[0]
    icon = actor_data.get("icon") or {}
    image = actor_data.get("image") or {}
    created_at = raw.get("created_at")
    return Account(id=str(raw["account_id"]),
                   username=username,
                   acct=raw["acct"],
                   display_name=actor_data.get("name") or username,
                   note=actor_data.get("summary") or "",
                   url=raw["actor_url"],
                   avatar=icon.get("url") if isinstance(icon, dict) else None,
                   avatar_static=icon.get("url") if isinstance(icon, dict) else None,
                   header=image.get("url") if isinstance(image, dict) else None,
                   header_static=image.get("url") if isinstance(image, dict) else None,
                   locked=actor_data.get("manuallyApprovesFollowers", False),
                   bot=actor_data.get("type") == "Service",
                   **({"created_at": created_at.isoformat()}
                      if hasattr(created_at, "isoformat") else
                      {}))

