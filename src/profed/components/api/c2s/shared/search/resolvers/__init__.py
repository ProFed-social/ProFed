# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
import asyncio
from typing import Optional
from .accounts import resolve as resolve_accounts
 

_RESOLVERS = {
    "accounts": resolve_accounts,
    # future: "statuses": resolve_statuses,
    # future: "hashtags": resolve_hashtags,
}
 
 
async def resolve_search(q:       str,
                         type:    Optional[str] = None,
                         resolve: bool          = False,
                         limit:   int           = 20) -> dict:
    active = {k: v for k, v in _RESOLVERS.items() if type is None or k == type}
    results = await asyncio.gather(*(fn(q, resolve=resolve, limit=limit)
                                     for fn in active.values()))
    merged: dict[str, list] = {}
    for key, items in ((k, i)
                       for result in results
                       for k, i in result.items()):
        merged.setdefault(key, []).extend(items)
    return merged
