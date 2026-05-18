# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import logging
from profed.components.api.c2s.shared.known_accounts.service import lookup_by_acct
from profed.components.api.c2s.shared.known_accounts.service import lookup_by_acct, make_account
from profed.models.mastodon import Account


logger = logging.getLogger(__name__)
 
 
async def resolve(q: str, resolve: bool = False, limit: int = 20) -> dict[str, Account]:
    if "@" not in q or not resolve:
        return {}

    acct = q.lstrip("@")
    row = await lookup_by_acct(acct)
    if row is None:
        return {}
    return {"accounts": [make_account(row)]}

