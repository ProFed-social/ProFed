# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import logging
import re
from profed.federation.webfinger import lookup_actor_url
from profed.identity import acct_from_username, actor_url_from_username, is_local
from profed.components.api.c2s.shared.actors.service import resolve_actor


logger = logging.getLogger(__name__)

_MENTION_RE = re.compile(r"(?<![\w.])@([A-Za-z0-9_~](?:[A-Za-z0-9._~!$&'()*+,;=-]*[A-Za-z0-9_~])?)"
                         r"(?:@([\w.-]+\.\w{2,}))?")

def parse_mentions(text: str) -> list[tuple[str, str | None]]:
    pairs = [(handle, host or None) for handle, host in _MENTION_RE.findall(text)]
    return list(dict.fromkeys(pairs))


async def _resolve_one(handle: str, host: str | None) -> tuple[str, str | None]:
    acct = handle if host is None else f"{handle}@{host}"
    if host is None or is_local(acct):
        exists = await resolve_actor(handle) is not None
        return acct_from_username(handle), (actor_url_from_username(handle) if exists else None)
    return acct, await lookup_actor_url(acct)


async def resolve_mentions(mentions: list[tuple[str, str | None]]) -> tuple[list[dict], list[str]]:
    resolved = await asyncio.gather(*(_resolve_one(handle, host) for handle, host in mentions))
    by_acct: dict[str, str | None] = {}
    for acct, url in resolved:
        by_acct.setdefault(acct, url)

    tag: list[dict] = []
    cc: list[str] = []
    for acct, url in by_acct.items():
        if url is None:
            logger.info("mention @%s could not be resolved; not federating it", acct)
            continue
        tag.append({"type": "Mention", "href": url, "name": f"@{acct}"})
        cc.append(url)
    return tag, cc

