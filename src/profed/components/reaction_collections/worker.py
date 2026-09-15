# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from profed.core.message_bus import message_bus
from profed.http.client import HttpClient
from profed.http.retry import due_at
from profed.topics.incoming_activities_topic import publish_incoming
from . import fetch


logger = logging.getLogger(__name__)


QUEUE_SIZE = 1000

ACCEPT = "application/activity+json"

_queue: asyncio.Queue = asyncio.Queue(maxsize=QUEUE_SIZE)
_config: dict = {}


def configure(config: dict) -> None:
    global _config
    _config = config


def _now() -> datetime:
    return datetime.now(timezone.utc)


def message_id_of(reaction_url: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, reaction_url)


async def _document(url: str) -> dict:
    response = await HttpClient().get(url, headers={"Accept": ACCEPT})
    return response.json()


async def _hand_on(reaction: dict) -> None:
    await publish_incoming(reaction["type"],
                           reaction["id"],
                           "",
                           reaction,
                           message_id_of(reaction["id"]))


async def _read(object_url: str, collection_url: str) -> int:
    collection = await _document(collection_url)
    items, following = fetch.start_of(collection)
    total = fetch.total_of(collection)
    seen = 0
    pages = 0

    while True:
        for reaction in fetch.reactions_of(items, object_url):
            await _hand_on(reaction)
        seen += len(items)
        pages += 1

        if following is None or fetch.enough(seen, pages, total, _config["max_pages"]):
            return seen

        items, following = fetch.page_of(await _document(following))


async def _report(state: str, object_url: str, next_due_at: datetime, attempt: int) -> None:
    async with message_bus().topic("reactions_resolution").publish() as publish:
        await publish(event_type=state,
                      object_id=object_url,
                      payload={"object_url": object_url,
                               "attempt": attempt,
                               "next_due_at": next_due_at.isoformat()})


async def _done(object_url: str, now: datetime) -> None:
    await _report("succeeded", object_url, now + _config["refresh_after"], 0)


async def _failed(object_url: str, attempt: int, now: datetime) -> None:
    await _report("failed", object_url, due_at(now, attempt + 1, _config), attempt + 1)


async def refresh(object_url: str, collection_url: str, attempt: int = 0) -> None:
    now = _now()
    try:
        logger.info("reaction_collections: read %d entries for %s",
                    await _read(object_url, collection_url),
                    object_url)
    except Exception:
        logger.warning("reaction_collections: could not read the reactions of %s", object_url, exc_info=True)
        await _failed(object_url, attempt, now)
    else:
        await _done(object_url, now)


async def enqueue(object_url: str, collection_url: str, attempt: int = 0) -> None:
    try:
        _queue.put_nowait((object_url, collection_url, attempt))
    except asyncio.QueueFull:
        logger.warning("reaction_collections: queue is full, dropping %s", object_url)
        await _failed(object_url, attempt, _now())


async def run() -> None:
    while True:
        await refresh(*await _queue.get())
        _queue.task_done()

