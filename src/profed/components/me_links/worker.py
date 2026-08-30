# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from datetime import datetime, timezone
from profed.core.message_bus import message_bus
from profed.core.workers import KeyedWorkers
from profed.topics.me_links_topic import link_id
from . import fetch, instance_key
from .storage import storage


logger = logging.getLogger(__name__)

_config = {}
_workers = None


def configure(config: dict) -> None:
    global _config
    _config = config


def workers() -> KeyedWorkers:
    global _workers
    if _workers is None:
        _workers = KeyedWorkers(step, name="me_links")
    return _workers


async def publish(event_type: str, profile_url: str, link_url: str, payload: dict) -> None:
    async with message_bus().topic("me_links").publish() as emit:
        await emit(event_type=event_type, object_id=link_id(profile_url, link_url), payload=payload)


def _stable_since(page, known: dict | None, now: datetime) -> datetime:
    unchanged = (known is not None
                 and page.etag is not None
                 and page.etag == known.get("etag"))
    same_body = (known is not None
                 and page.content_hash is not None
                 and page.content_hash == known.get("content_hash"))
    return known["stable_since"] if (unchanged or same_body) else now


async def _publish_result(profile_url, link_url, state, page, known, now) -> None:
    stable_since = known["stable_since"] if page.state == "unchanged" else _stable_since(page, known, now)

    await publish(state,
                  profile_url,
                  link_url,
                  {"checked_at": now.isoformat(),
                   "stable_since": stable_since.isoformat(),
                   "last_modified": page.last_modified or (known or {}).get("last_modified"),
                   "etag": page.etag or (known or {}).get("etag"),
                   "content_hash": page.content_hash or (known or {}).get("content_hash")})


def _state_of(page, known, profile_url: str) -> str | None:
    return (None
            if page.state == "failed" else
            "gone"
            if page.state == "gone" else
            (known or {}).get("state", "unverified")
            if page.state == "unchanged" else
            "verified"
            if fetch.points_back(page.links, profile_url) else
            "unverified")


async def check(profile_url: str, link_url: str, now: datetime) -> bool:
    known = await (await storage()).verification(profile_url, link_url)
    page = await fetch.perform(link_url, known, instance_key.signer())
    state = _state_of(page, known, profile_url)

    if state is None:
        return False

    await _publish_result(profile_url, link_url, state, page, known, now)
    return True


async def step(key, queue) -> float | None:
    profile_url, link_url = key
    while not queue.empty():
        queue.get_nowait()

    known = await (await storage()).verification(profile_url, link_url)
    now = datetime.now(timezone.utc)
    if known is not None and known["next_due_at"] > now:
        return None

    return None if await check(profile_url, link_url, now) else float(_config.get("retry_wait", 300))

