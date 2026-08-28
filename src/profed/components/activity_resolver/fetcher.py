# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import random
import re
import uuid
from collections import namedtuple
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from profed.core.message_bus import message_bus
from profed.http.client import HttpClient
from profed.http.retry import backoff
from profed.topics.incoming_activities_topic import publish_incoming
from .storage import storage

REQUEST_TIMEOUT = 30.0
LEASE = 120.0
MAX_TOTAL = 172800
GRACE = 2 * MAX_TOTAL
TOMBSTONE_THRESHOLD = 9
DEFAULT_LIFETIME = 3600
SLEEP_MIN = 10.0
SLEEP_MAX = 30.0
IDLE_LIMIT = 15
MAX_ATTEMPTS = 10

_config: dict = {}
_queues: dict = {}
_tasks: dict = {}
_started = False


Reference = namedtuple("Reference", "referrer sought inherited sign")


def _wait_window(row) -> float:
    return (float(_config.get("lease", LEASE))
            if row["state"] == "attempting" else
            backoff(row["attempt"], _config)
            if row["state"] in ("failed", "not_found") else
            0.0)


def _fresh(row, sought_version, now) -> bool:
    return (row["version"] is not None and sought_version <= row["version"]
            if sought_version is not None else
            now < row["version"]
            if row["state"] == "tombstone" else
            row["cache_end"] is not None and now < row["cache_end"])


def _decide(row, sought_version, now) -> tuple:
    return (("claim", 1)
            if row is None else
            ("skip", None)
            if _fresh(row, sought_version, now) else
            ("claim", row["attempt"] + 1)
            if now >= row["emitted_at"] + timedelta(seconds=_wait_window(row)) else
            ("wait", None))


def _object_version(obj):
    return obj.get("updated") or obj.get("published")


def _max_age(response):
    match = re.search(r"max-age=(\d+)", response.headers.get("Cache-Control", ""))
    return int(match.group(1)) if match else None


def _host(url):
    return urlparse(url).hostname


def _from_object(obj, url, max_age) -> tuple:
    return (("failed", None, None)
            if isinstance(obj, dict) and _host(obj.get("id", "")) != _host(url) else
            ("tombstone", obj, None)
            if isinstance(obj, dict) and obj.get("type") == "Tombstone" else
            ("succeeded", obj, max_age))


async def _fetch(url, sign=None) -> tuple:
    try:
        response = await HttpClient().get(url,
                                          headers={"Accept": "application/activity+json"},
                                          timeout=REQUEST_TIMEOUT,
                                          sign=sign,
                                          raise_for_status=False)

        return (_from_object(response.json(), url, _max_age(response))
                if response.is_success else
                ("tombstone", None, None)
                if response.status_code == 410 else
                ("not_found", None, None)
                if response.status_code == 404 else
                ("failed", None, None))
    except Exception:
        return ("failed", None, None)


def _threshold() -> int:
    return int(_config.get("tombstone_threshold", TOMBSTONE_THRESHOLD))


def _tombstone_version(now) -> str:
    return (now + timedelta(seconds=int(_config.get("grace", GRACE)))).isoformat()


def _cache_end(now, max_age) -> str:
    lifetime = max_age if max_age is not None else int(_config.get("default_lifetime", DEFAULT_LIFETIME))
    return (now + timedelta(seconds=lifetime)).isoformat()


def _transition(result, obj, attempt, not_found_count, inherited, now, max_age) -> tuple:
    return (("succeeded", _object_version(obj) or inherited, _cache_end(now, max_age), 0, 0)
            if result == "succeeded" else
            ("tombstone", _tombstone_version(now), None, 0, 0)
            if result == "tombstone" or (result == "not_found" and not_found_count + 1 >= _threshold()) else
            ("not_found", None, None, attempt, not_found_count + 1)
            if result == "not_found" else
            ("failed", None, None, attempt, not_found_count))


def _resolution_id(object_id, referrer_id, attempt, state):
    return uuid.uuid5(uuid.NAMESPACE_URL, f"{object_id}#{referrer_id}#{attempt}#{state}")


async def _emit(state, object_id, referrer_id, attempt, version, not_found_count, cache_end=None):
    async with message_bus().topic("resolution").publish() as publish:
        return await publish(event_type=state,
                             object_id=object_id,
                             payload={"object_id": object_id,
                                      "version": version,
                                      "cache_end": cache_end,
                                      "attempt": attempt,
                                      "not_found_count": not_found_count},
                             message_id=_resolution_id(object_id, referrer_id, attempt, state))


async def _claim(object_id, referrer_id, attempt, not_found_count) -> bool:
    return await _emit("attempting", object_id, referrer_id, attempt, None, not_found_count) is not None


def _backfeed_id(object_id, version):
    return uuid.uuid5(uuid.NAMESPACE_URL, f"{object_id}#{version}")


async def _backfeed(obj, version) -> None:
    await publish_incoming("Update",
                           obj["id"],
                           "",
                           {"actor": obj.get("attributedTo"), "object": obj},
                           _backfeed_id(obj["id"], version))


async def _sleep() -> None:
    await asyncio.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX))


def _absorb(queue, current):
    latest = current
    while not queue.empty():
        reference = queue.get_nowait()
        if current is None or reference.referrer != current.referrer:
            latest = reference
    return latest


def _max_attempts() -> int:
    return int(_config.get("max_attempts", MAX_ATTEMPTS))


async def _resolve(object_id, reference, attempt, not_found_count, now) -> None:
    if await _claim(object_id, reference.referrer, attempt, not_found_count):
        result, obj, max_age = await _fetch(object_id, reference.sign)
        state, version, cache_end, out_attempt, out_not_found_count = _transition(result,
                                                                                  obj,
                                                                                  attempt,
                                                                                  not_found_count,
                                                                                  reference.inherited,
                                                                                  now,
                                                                                  max_age)
        await _emit(state, object_id, reference.referrer, out_attempt, version, out_not_found_count, cache_end)

        if state == "succeeded":
            await _backfeed(obj, version)


async def _step(object_id, reference, fresh, row, now):
    action, attempt = _decide(row, reference.sought, now)

    if action == "skip":
        return None
    if action == "wait":
        await _sleep()
        return reference

    attempt = 1 if fresh else attempt
    if attempt > _max_attempts():
        return None

    await _resolve(object_id, reference, attempt, row["not_found_count"] if row else 0, now)
    await _sleep()
    return reference


async def _run(object_id) -> None:
    queue = _queues[object_id]
    reference = None
    idle = 0

    while True:
        previous, reference = reference, _absorb(queue, reference)

        if reference is None:
            idle += 1
            if idle < IDLE_LIMIT:
                await _sleep()
                continue
            await _sleep()
            if _queues[object_id].empty():
                return
            idle = 0
            continue

        idle = 0

        reference = await _step(object_id,
                                reference,
                                reference is not previous,
                                row=await (await storage()).get(object_id),
                                now=datetime.now(timezone.utc))


def _spawn(object_id) -> None:
    task = asyncio.create_task(_run(object_id), name=f"resolve:{object_id}")
    _tasks[object_id] = task
    task.add_done_callback(
        lambda t: _tasks.pop(object_id, None) if _tasks.get(object_id) is t else None)


def ensure_task(object_id) -> None:
    if _started and object_id not in _tasks:
        _spawn(object_id)


def start(config: dict) -> None:
    global _config, _started
    _config = config
    for object_id in list(_queues):
        _spawn(object_id)
    _started = True


def enqueue(object_id, referrer_id, sought_version, inherited, sign) -> None:
    _queues.setdefault(object_id, asyncio.Queue()).put_nowait(Reference(referrer_id, sought_version, inherited, sign))
    ensure_task(object_id)

