# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.federation.webfinger import lookup_acct


async def resolve(payload: dict, followers: set[str]) -> set[str]:
    obj = payload.get("object")
    if not isinstance(obj, dict):
        return set()

    actor_url = obj.get("object")
    if not actor_url or not isinstance(actor_url, str):
        return set()

    acct = await lookup_acct(actor_url)
    return {acct} if acct else set()

