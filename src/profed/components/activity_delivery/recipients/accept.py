# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from typing import Callable, Awaitable
from profed.federation.webfinger import lookup_acct


async def resolve(payload: dict, followers: set[str]) -> set[str]:
    actor_url = payload.get("object", {}).get("actor")
    if not actor_url:
        return set()
    acct = await lookup_acct(actor_url)
    return {acct} if acct else set()
 
