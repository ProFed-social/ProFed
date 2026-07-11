# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timezone
from typing import Optional
from profed.core.message_bus import message_bus
from profed.federation.webfinger import lookup_acct
from profed.http.client import HttpClient
from profed.identity import account_id as compute_account_id, is_local
from profed.sanitize import sanitize_document


async def fetch_actor(actor_url: str, sign=None) -> Optional[dict]:
    try:
        return (await HttpClient().get(actor_url,
                                       headers={"Accept": "application/activity+json"},
                                       timeout=10.0,
                                       sign=sign)).json()
    except Exception:
        return None


async def fetch_and_register_actor(actor_url: str, sign=None) -> Optional[dict]:
    actor_data = await fetch_actor(actor_url, sign)
    if actor_data is None:
        return None
    actor_data = sanitize_document(actor_data)

    acct = await lookup_acct(actor_url, sign)
    if acct is not None and not is_local(acct):
        aid = int(compute_account_id(acct))
        payload = {"acct": acct,
                   "actor_url": actor_url,
                   "actor_data": actor_data,
                   "last_webfinger_at": datetime.now(timezone.utc).isoformat()}
        async with message_bus().topic("remote_actors").publish() as publish:
            await publish(event_type="discovered", object_id=str(aid), payload=payload)

    return actor_data

