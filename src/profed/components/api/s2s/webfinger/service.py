# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Callable
from urllib.parse import urlparse
from profed.identity import (username_from_acct,
                             actor_url_from_username,
                             acct_from_username,
                             domain)
from profed.components.api.s2s.webfinger.storage import storage


async def _from_username(username: str, conversion: Callable[[str], str | None]) -> str | None:
    if await (await storage()).exists(username):
        return conversion(username)
    return None


async def resolve_actor_url(acct: str):
    return await _from_username(username_from_acct(acct), actor_url_from_username)


async def resolve_acct_from_actor_url(actor_url: str) -> str | None:
    """Return acct if the actor_url maps to a local user, None otherwise."""
    parsed = urlparse(actor_url)
    if parsed.netloc != domain():
        return None

    parts = parsed.path.strip("/").split("/")
    if len(parts) != 2 or parts[0] != "actors":
        return None

    return await _from_username(parts[1], acct_from_username)

