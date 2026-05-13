# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import logging
from profed.components.api.c2s.shared.known_accounts.service import lookup_by_acct
from profed.identity import account_id
from profed.models.mastodon import Account


logger = logging.getLogger(__name__)
 
 
def _actor_to_account(actor: dict, acct: str) -> Account:
    username, _ = acct.split("@", 1)
    return Account(id=account_id(acct),
                   username=username,
                   acct=acct,
                   display_name=actor.get("name") or username,
                   note=actor.get("summary") or "",
                   url=actor.get("url") or actor.get("id", ""))
 
 
async def resolve(q: str, resolve: bool = False, limit: int = 20) -> dict[str, Account]:
    if "@" not in q or not resolve:
        return {}

    acct = q.lstrip("@")
    row = await lookup_by_acct(acct)
    if row is None:
        return {}
    actor = row.get("actor_data") or {}
    return {"accounts": [_actor_to_account(actor, acct)]}

