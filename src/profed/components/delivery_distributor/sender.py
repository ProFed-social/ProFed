# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import httpx
import json
import logging
import random
import time
import uuid
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
from typing import Optional

from profed.http.client import HttpClient
from profed.http.signatures import sign_request
from profed.sanitize import sanitize_egress, sanitize_as_object
from profed.core.message_bus import message_bus
from .storage import storage


logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30.0
LEASE = 120.0
SLEEP_MIN = 10.0
SLEEP_MAX = 30.0
IDLE_LIMIT = 15
INITIAL_RETRY = 300
RETRY_MULTIPLIER = 2
MAX_RETRY = 86400
MAX_TOTAL = 172800
INBOX_CACHE_TTL_MEAN = 3600.0
INBOX_CACHE_TTL_JITTER = 0.10

_INTERNAL_FIELDS = {"username"}

_config: dict = {}
_started = False
_registry: dict[str, asyncio.Task] = {}
_inbox_cache: dict[str, tuple[str, float]] = {}


def _actor_url_from_acct(acct: str) -> str:
    username, host = acct.split("@", 1)
    return f"https://{host}/users/{username}"


async def _fetch_inbox_url(actor_url: str) -> Optional[str]:
    now = time.monotonic()
    cached = _inbox_cache.get(actor_url)
    if cached is not None and now < cached[1]:
        return cached[0]
    try:
        data = (await HttpClient().get(actor_url,
                                       headers={"Accept": "application/activity+json"},
                                       timeout=REQUEST_TIMEOUT)).json()
        inbox = data.get("inbox")
        if isinstance(inbox, str):
            mean = float(_config.get("inbox_cache_ttl", INBOX_CACHE_TTL_MEAN))
            jitter = float(_config.get("inbox_cache_ttl_jitter", INBOX_CACHE_TTL_JITTER))
            _inbox_cache[actor_url] = (inbox, now + mean * random.uniform(1 - jitter, 1 + jitter))
            return inbox
    except Exception:
        logger.warning("Failed to fetch actor %s", actor_url)
    return None


async def _build_signed_headers(activity: dict, inbox_url: str, body: bytes) -> dict[str, str]:
    username = activity.get("actor", "").rstrip("/").split("/")[-1]
    keys = await (await storage()).get_user_key(username)
    headers = {"Content-Type": "application/activity+json"}
    if keys is not None:
        headers.update(sign_request("POST",
                                    inbox_url,
                                    body,
                                    f"{activity.get('actor', '')}#main-key",
                                    keys[1]))
    else:
        headers["Host"] = urlparse(inbox_url).netloc
    return headers


async def _post_to_inbox(inbox_url: str, activity: dict) -> httpx.Response:
    ap_activity = {k: v for k, v in activity.items() if k not in _INTERNAL_FIELDS}
    if "@context" not in ap_activity:
        ap_activity["@context"] = "https://www.w3.org/ns/activitystreams"
    body = json.dumps(sanitize_egress(ap_activity, sanitize_as_object, "delivery")).encode()
    return await HttpClient().post(inbox_url,
                                   content=body,
                                   headers=await _build_signed_headers(activity, inbox_url, body),
                                   timeout=REQUEST_TIMEOUT,
                                   raise_for_status=False)


def _backoff(attempt: int) -> float:
    initial = int(_config.get("initial_retry", INITIAL_RETRY))
    mult = float(_config.get("retry_multiplier", RETRY_MULTIPLIER))
    max_wait = int(_config.get("max_retry", MAX_RETRY))
    return min(initial * (mult ** (attempt - 1)), max_wait)


def _decide(head: dict, now: datetime) -> tuple:
    attempt = head["attempt"]
    if attempt == 0:
        return ("claim", 1)

    first_at = head["first_attempt_at"]
    max_total = int(_config.get("max_total", MAX_TOTAL))
    if first_at is not None and (now - first_at).total_seconds() > max_total:
        return ("give_up", attempt)

    if head["failed_at"] is not None:
        due = head["failed_at"] + timedelta(seconds=_backoff(attempt))
        return ("claim", attempt + 1) if now >= due else ("wait",)

    lease = float(_config.get("lease", LEASE))
    if head["attempt_at"] is not None and now < head["attempt_at"] + timedelta(seconds=lease):
        return ("wait",)
    return ("claim", attempt + 1)


async def _publish(event_type: str, activity_id: str, recipient: str,
                   attempt: int, message_id) -> Optional[int]:
    async with message_bus().topic("deliveries").publish() as publish:
        return await publish(event_type=event_type,
                             object_id=f"{activity_id}|{recipient}",
                             payload={"attempt": attempt},
                             message_id=message_id)


async def _claim(activity_id: str, recipient: str, attempt: int) -> bool:
    message_id = uuid.uuid5(uuid.NAMESPACE_URL, f"{activity_id}#{recipient}#{attempt}#attempting")
    return await _publish("attempting", activity_id, recipient, attempt, message_id) is not None


async def _deliver(head: dict, recipient: str) -> bool:
    inbox_url = await _fetch_inbox_url(_actor_url_from_acct(recipient))
    if inbox_url is None:
        return False
    try:
        response = await _post_to_inbox(inbox_url, head["activity"])
        return 200 <= response.status_code < 300
    except Exception:
        logger.exception("HTTP error delivering %s -> %s", head["activity_id"], recipient)
        return False


async def _sleep() -> None:
    await asyncio.sleep(random.uniform(SLEEP_MIN, SLEEP_MAX))


async def _run(recipient: str) -> None:
    idle = 0
    while True:
        head = await (await storage()).head(recipient)

        if head is None:
            idle += 1
            if idle >= IDLE_LIMIT:
                if _registry.get(recipient) is asyncio.current_task():
                    _registry.pop(recipient, None)
                await _sleep()
                if await (await storage()).head(recipient) is None:
                    return
                idle = 0
                continue
            await _sleep()
            continue

        idle = 0
        activity_id = head["activity_id"]
        action = _decide(head, datetime.now(timezone.utc))

        if action[0] == "wait":
            await _sleep()
            continue

        if action[0] == "give_up":
            await _publish("gave_up", activity_id, recipient, action[1],
                           uuid.uuid5(uuid.NAMESPACE_URL, f"{activity_id}#{recipient}#gave_up"))
            await (await storage()).dequeue(recipient, activity_id)
            continue

        attempt = action[1]
        if not await _claim(activity_id, recipient, attempt):
            await _sleep()
            continue

        if await _deliver(head, recipient):
            await _publish("done", activity_id, recipient, attempt,
                           uuid.uuid5(uuid.NAMESPACE_URL, f"{activity_id}#{recipient}#done"))
            await (await storage()).dequeue(recipient, activity_id)
            continue

        await _publish("failed", activity_id, recipient, attempt,
                       uuid.uuid5(uuid.NAMESPACE_URL, f"{activity_id}#{recipient}#{attempt}#failed"))
        await _sleep()


def _spawn(recipient: str) -> None:
    task = asyncio.create_task(_run(recipient), name=f"delivery:{recipient}")
    _registry[recipient] = task
    task.add_done_callback(
        lambda t: _registry.pop(recipient, None) if _registry.get(recipient) is t else None)


def ensure_task(recipient: str) -> None:
    if _started and recipient not in _registry:
        _spawn(recipient)


def start(config: dict, recipients: set[str]) -> None:
    global _config, _started
    _config = config
    for recipient in recipients:
        _spawn(recipient)
    _started = True

