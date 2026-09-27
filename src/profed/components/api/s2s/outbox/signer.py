# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Optional
from profed.core.message_bus import message_bus
from profed.http.signatures import key_id_from_signature_header, verify_request
from profed.identity import is_local_url
from profed.topics.unknown_actors_topic import throttled_id
from .signers_storage import storage


logger = logging.getLogger(__name__)

MAX_SIGNATURE_AGE = timedelta(hours=12)


async def request_actor(actor_url: str) -> None:
    if is_local_url(actor_url):
        logger.warning("outbox: a read request was signed with a local key: %s", actor_url)
    else:
        async with message_bus().topic("unknown_actors").publish() as publish:
            await publish(event_type="discovered_url",
                          object_id=actor_url,
                          payload={},
                          message_id=throttled_id("outbox", actor_url))


def _signed_recently(headers: dict, now: datetime) -> bool:
    try:
        signed_at = parsedate_to_datetime(headers.get("date", ""))
    except (TypeError, ValueError):
        return False

    return abs(now - signed_at) <= MAX_SIGNATURE_AGE


async def signer_of(method: str, path: str, headers: dict, now: Optional[datetime] = None) -> Optional[dict]:
    lowered = {key.lower(): value for key, value in headers.items()}
    actor_url = key_id_from_signature_header(lowered.get("signature", ""))
    if actor_url is None:
        return None

    if not _signed_recently(lowered, now or datetime.now(timezone.utc)):
        logger.warning("outbox: the signature of %s is outside the accepted time window", actor_url)
        return None

    known = await (await storage()).signer(actor_url)
    if known is None:
        logger.warning("outbox: no public key for %s, requesting resolution", actor_url)
        await request_actor(actor_url)
        return None

    if not verify_request(method, path, lowered, b"", known["public_key_pem"]):
        logger.warning("outbox: signature of %s does not match the stored key", actor_url)
        await request_actor(actor_url)
        return None

    return known

