# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from profed.models.mastodon import Account
from .storage import storage
 
 
async def resolve_actor(username: str) -> Account | None:
    payload = await (await storage()).fetch(username)
    return (Account.model_validate(payload)
            if payload is not None else
            None)


def with_source(account: Account) -> Account:
    return account.model_copy(update={"source": {"privacy": "public",
                                                 "sensitive": False,
                                                 "language": None,
                                                 "note": account.note or "",
                                                 "fields": []}})

