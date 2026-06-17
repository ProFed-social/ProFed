# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from profed.models.mastodon import Account
from .storage import storage
 
 
async def resolve_actor(username: str) -> Account | None:
    payload = await (await storage()).fetch(username)
    return (Account.model_validate(payload)
            if payload is not None else
            None)

async def resolve_actor_by_id(account_id: str) -> Account | None:
    payload = await (await storage()).fetch_by_id(account_id)
    if payload is None:
        return None
    return Account.model_validate(payload)


async def resolve_actor_by_url(url: str) -> Account | None:
    payload = await (await storage()).fetch_by_url(url)
    if payload is None:
        return None
    return Account.model_validate(payload)


def with_source(account: Account) -> Account:
    return account.model_copy(update={"source": {"privacy": "public",
                                                 "sensitive": False,
                                                 "language": None,
                                                 "note": account.note or "",
                                                 "fields": []}})

