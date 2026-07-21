# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional
from profed.federation.webfinger import lookup_actor_url
from profed.federation.actors import fetch_and_register_actor
from profed.http.signatures import make_sign
from profed.identity import is_local
from .storage import storage
from .instance_key import signing_key


def _signer():
    key = signing_key()
    return make_sign(*key) if key else None


async def lookup(acct: str) -> Optional[str]:
    url = await (await storage()).url_for(acct)
    if url is not None:
        return url
    if is_local(acct):
        return None

    sign = _signer()
    actor_url = await lookup_actor_url(acct, sign)
    if actor_url is not None:
        await fetch_and_register_actor(actor_url, sign)
    return actor_url

