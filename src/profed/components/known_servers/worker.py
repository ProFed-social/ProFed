# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from datetime import datetime, timezone
from profed.core.message_bus import message_bus
from profed.core.workers import KeyedWorkers
from . import fetch
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
        _workers = KeyedWorkers(step, name="known_servers")
    return _workers


async def publish(event_type: str, host: str, payload: dict) -> None:
    async with message_bus().topic("known_servers").publish() as emit:
        await emit(event_type=event_type, object_id=host, payload=payload)


def _stable_since(info, known: dict | None, now: datetime) -> datetime:
    unchanged = (known is not None
                 and info.etag is not None
                 and info.etag == known.get("etag"))
    same_body = (known is not None
                 and info.content_hash is not None
                 and info.content_hash == known.get("content_hash"))
    return known["stable_since"] if (unchanged or same_body) else now


def _carried(info, known: dict | None, now: datetime, failures: int) -> dict:
    return {"checked_at": now.isoformat(),
            "stable_since": (known["stable_since"]
                             if info.state != "read" and known is not None else
                             _stable_since(info, known, now)).isoformat(),
            "failures": failures,
            "last_modified": info.last_modified or (known or {}).get("last_modified"),
            "etag": info.etag or (known or {}).get("etag"),
            "content_hash": info.content_hash or (known or {}).get("content_hash")}


async def _failed(host: str, known: dict | None, now: datetime) -> None:
    failures = (known or {}).get("failures", 0) + 1
    await publish("unreachable", host, _carried(fetch.NodeInfo("failed"), known, now, failures))
    if failures >= int(_config.get("give_up_after", 10)):
        await publish("lost", host, {})


async def _succeeded(host: str, info, known: dict | None, now: datetime) -> None:
    await publish("updated",
                  host,
                  dict(_carried(info, known, now, 0),
                       software=info.software or (known or {}).get("software"),
                       features=info.features))


async def check(host: str, now: datetime) -> None:
    known = await (await storage()).check_of(host)
    info = await fetch.perform(host, known)

    if info.state == "failed":
        await _failed(host, known, now)
    elif info.state == "unchanged":
        await publish("updated", host, _carried(info, known, now, 0))
    else:
        await _succeeded(host, info, known, now)


async def step(key, queue) -> float | None:
    while not queue.empty():
        queue.get_nowait()

    now = datetime.now(timezone.utc)
    known = await (await storage()).check_of(key)
    if known is not None and known["next_due_at"] > now:
        return None

    await check(key, now)
    return None

