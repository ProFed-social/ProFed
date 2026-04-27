# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import asyncio
import httpx
import logging
import random
import time
import json
from urllib.parse import urlparse
from email.utils import parsedate_to_datetime
from typing import Optional
 
from profed.http.client import http 
from profed.http.signatures import sign_request
from profed.core.message_bus import message_bus
from .projections import get_delivery_status
from .storage import storage
 
 
logger = logging.getLogger(__name__)
 
INITIAL_RETRY          = 300
RETRY_MULTIPLIER       = 2
MAX_RETRY              = 86400
MAX_TOTAL              = 172800
REQUEST_TIMEOUT        = 30.0
INBOX_CACHE_TTL_MEAN   = 3600.0
INBOX_CACHE_TTL_JITTER = 0.10
 
PERMANENT_FAILURES = {403, 404, 410}
 

_inbox_cache: dict[str, tuple[str, float, float]] = {}
 
 
async def _fetch_inbox_url(actor_url: str, config: dict) -> Optional[str]:
    now = time.monotonic()
    cached = _inbox_cache.get(actor_url)
    if cached is not None and now < cached[2]:
        return cached[0]
    try:
        data  = await http("GET").json(actor_url,
                                        headers={"Accept": "application/activity+json"},
                                        timeout=REQUEST_TIMEOUT)
        inbox = data.get("inbox")
        if isinstance(inbox, str):
            mean   = float(config.get("inbox_cache_ttl", INBOX_CACHE_TTL_MEAN))
            jitter = float(config.get("inbox_cache_ttl_jitter", INBOX_CACHE_TTL_JITTER))
            ttl    = mean * random.uniform(1 - jitter, 1 + jitter)
            _inbox_cache[actor_url] = (inbox, now, now + ttl)
            return inbox
    except Exception:
        logger.warning("Failed to fetch actor %s", actor_url)
    return None
 
 
def _next_delay(config: dict,
                status: dict | None,
                retry_after: int | None) -> int | None:
    """Return seconds to wait before next attempt, or None to give up."""
    initial  = int(config.get("initial_retry",    INITIAL_RETRY))
    mult     = float(config.get("retry_multiplier", RETRY_MULTIPLIER))
    max_wait = int(config.get("max_retry",        MAX_RETRY))
    max_tot  = int(config.get("max_total",        MAX_TOTAL))
 
    if status is None:
        return 0
 
    first_attempt_at = status.get("first_attempt_at", time.time())
    if time.time() - first_attempt_at > max_tot:
        return None
 
    attempt = status["attempt"]
    base    = retry_after if retry_after and retry_after > initial else initial
    return min(int(base * (mult ** (attempt - 1))), max_wait)
 
 
def _parse_retry_after(headers) -> int | None:
    value = headers.get("retry-after")
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        pass
    try:
        dt = parsedate_to_datetime(value)
        return max(0, int(dt.timestamp() - time.time()))
    except Exception:
        return None
 
 
async def _publish_attempt(activity_id: str,
                            recipient: str,
                            attempt: int,
                            success: bool,
                            status_code: int | None,
                            retry_after: int | None,
                            first_attempt_at: float) -> None:
    async with message_bus().topic("deliveries").publish() as publish:
        await publish({"type": "attempted",
                       "payload": {"activity_id":      activity_id,
                                   "recipient":        recipient,
                                   "success":          success,
                                   "attempt":          attempt,
                                   "status_code":      status_code,
                                   "retry_after":      retry_after,
                                   "first_attempt_at": first_attempt_at}})
 


async def _build_signed_headers(activity: dict,
                                inbox_url: str,
                                body: bytes) -> dict[str, str]:
    username = activity.get("actor", "").rstrip("/").split("/")[-1]
    keys     = await (await storage()).get_user_key(username)
    headers  = {"Content-Type": "application/activity+json",
                "Host":         urlparse(inbox_url).netloc}
    if keys is not None:
        headers.update(sign_request("POST",
                                    inbox_url,
                                    body,
                                    f"{activity.get('actor', '')}#main-key",
                                    keys[1]))
    return headers


async def _post_to_inbox(inbox_url: str,
                         activity: dict,
                         client: httpx.AsyncClient) -> httpx.Response:
    body    = json.dumps(activity).encode()
    headers = await _build_signed_headers(activity, inbox_url, body)
    logger.debug("POST %s headers: %r", inbox_url, headers)

    return await client.post(inbox_url,
                             content=body,
                             headers=headers,
                             timeout=REQUEST_TIMEOUT)


async def _attempt_delivery(config: dict,
                            activity_id: str,
                            activity: dict,
                            recipient_acct: str,
                            attempt: int,
                            first_at: float) -> None:
    inbox_url = await _fetch_inbox_url(_actor_url_from_acct(recipient_acct),
                                       config)
    if inbox_url is None:
        await _publish_attempt(activity_id, recipient_acct, attempt, False, None, None, first_at)
        return

    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await _post_to_inbox(inbox_url, activity, client)

        status_code = response.status_code
        success     = 200 <= status_code < 300
        await _publish_attempt(activity_id,
                               recipient_acct,
                               attempt,
                               success,
                               status_code,
                               _parse_retry_after(response.headers),
                               first_at)

        if not success and not status_code in PERMANENT_FAILURES:
            asyncio.create_task(deliver(config, activity_id, activity, recipient_acct),
                                name=f"retry:{activity_id}:{recipient_acct}")
    except Exception:
        logger.exception("HTTP error delivering %s → %s", activity_id, recipient_acct)

        await _publish_attempt(activity_id, recipient_acct, attempt, False, None, None, first_at)
        asyncio.create_task(deliver(config, activity_id, activity, recipient_acct),
                            name=f"retry:{activity_id}:{recipient_acct}")


async def deliver(config: dict,
                   activity_id: str,
                   activity: dict,
                   recipient_acct: str) -> None:
    status = await get_delivery_status(activity_id, recipient_acct)
 
    if status is not None and status["success"]:
        return
 
    attempt  = 1 if status is None else status["attempt"] + 1
    delay = _next_delay(config, status, status.get("retry_after") if status else None)
    if delay is None:
        logger.warning("Giving up on %s → %s after %d attempts",
                       activity_id, recipient_acct, attempt - 1)
        return
 
    if delay > 0:
        await asyncio.sleep(delay)

    await _attempt_delivery(config, activity_id, activity, recipient_acct, attempt, time.time() if status is None else status["first_attempt_at"]) 
 
 
def _actor_url_from_acct(acct: str) -> str:
    username, host = acct.split("@", 1)
    return f"https://{host}/users/{username}"

