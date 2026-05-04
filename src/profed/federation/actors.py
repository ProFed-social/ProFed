# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timezone
from typing import Optional
from profed.core.message_bus import message_bus
from profed.federation.webfinger import lookup_acct
from profed.http.client import http
from profed.identity import account_id as compute_account_id


async def fetch_actor(actor_url: str) -> Optional[dict]:
    try:
        return await http("GET").json(actor_url,
                                      headers={"Accept": "application/activity+json"},
                                      timeout=10.0)
    except Exception:
        return None


async def fetch_and_register_actor(actor_url: str) -> Optional[str]:
    actor_data = await fetch_actor(actor_url)
    if actor_data is None:
        return None

    acct = await lookup_acct(actor_url)
    if acct is not None:
        aid = int(compute_account_id(acct))
        async with message_bus().topic("known_accounts").publish() as publish:
            await publish({"type": "discovered",
                           "payload": {"account_id": aid,
                                       "acct": acct,
                                       "actor_url": actor_url,
                                       "actor_data": actor_data,
                                       "last_webfinger_at": datetime.now(timezone.utc).isoformat()}})

    return (actor_data.get("publicKey") or {}).get("publicKeyPem")

