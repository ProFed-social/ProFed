# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.components.api.storage.webfinger import storage
from profed.components.api.identity import username_from_acct, actor_url_from_username


async def resolve_actor_url(acct: str):
    username = username_from_acct(acct)
    wfs = await storage()
    if await wfs.user_exists(username):
        return actor_url_from_username(username)
    return None

