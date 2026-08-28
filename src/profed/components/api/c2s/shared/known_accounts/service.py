# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional
from profed.core.message_bus import message_bus
from profed.identity import is_local
from profed.topics.unknown_actors_topic import throttled_id
from .storage import storage
from profed.models.mastodon import Account


WEBFINGER_CACHE_TTL = 86400


async def request_resolution(event_type: str, name: str) -> None:
    async with message_bus().topic("unknown_actors").publish() as publish:
        await publish(event_type=event_type,
                      object_id=name,
                      payload={},
                      message_id=throttled_id("known_accounts", name))


async def _request_acct(acct: str) -> None:
    if not is_local(acct):
        await request_resolution("discovered_acct", acct)


async def _request_actor_url(actor_url: str) -> None:
    await request_resolution("discovered_url", actor_url)


async def _request_if(test, result, callback, *args, **kwargs):
    if test:
        await callback(*args, **kwargs)
    return result


async def _request_if_none(result, callback, *args, **kwargs):
    return await _request_if(result is None, result, callback, *args, **kwargs)


def _is_fresh(row: dict, ttl: int) -> bool:
    if is_local(row.get("acct") or ""):
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


async def lookup_by_id(account_id: int, config: dict | None = None) -> Optional[Account]:
    row = await (await storage()).get_by_id(account_id)
    if row is not None:
        return _account_from_row(await _request_if(not _is_fresh(row, _ttl(config)), row, _request_acct, row["acct"]))


async def lookup_by_acct(acct: str, config: dict | None = None) -> Optional[Account]:
    row = await _request_if_none(await (await storage()).get_by_acct(acct), _request_acct, acct)
    if row is not None:
        return _account_from_row(await _request_if(not _is_fresh(row, _ttl(config)), row, _request_acct, acct))


async def lookup_by_actor_url(actor_url: str, config: dict | None = None) -> Optional[Account]:
    row = await _request_if_none(await (await storage()).get_by_actor_url(actor_url), _request_actor_url, actor_url)
    if row is not None:
        return _account_from_row(await _request_if(not _is_fresh(row, _ttl(config)), row, _request_actor_url, actor_url))


async def lookup_multiple(actor_urls: list[str], config: dict | None = None) -> dict[str, Account]:
    return {u: a
            for u, a in zip(actor_urls, await asyncio.gather(*(lookup_by_actor_url(u, config) for u in actor_urls)))
            if a is not None}


async def cached_by_actor_url(actor_url: str) -> Optional[Account]:
    row = await (await storage()).get_by_actor_url(actor_url)
    return _account_from_row(row) if row is not None else None


async def cached_multiple(actor_urls: list[str]) -> dict[str, Account]:
    return {url: account
            for url, account in zip(actor_urls, await asyncio.gather(*(cached_by_actor_url(url) for url in actor_urls)))
            if account is not None}

