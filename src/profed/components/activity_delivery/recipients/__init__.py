# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later
 
from typing import Callable, Awaitable
from .accept import resolve as resolve_accept
from .follow import resolve as resolve_follow 

_RESOLVERS: dict[str, Callable[[dict, set[str]], Awaitable[set[str]]]] = {
    "Accept": resolve_accept,
    "Follow": resolve_follow,
    # future entries:
    # "Create":   _resolve_create,   # notes: followers + mentions + reply-to author
    # "Like":     _resolve_like,      # followers + liked activity author
    # "Announce": _resolve_announce,  # followers + boosted activity author
    # "Undo":     _resolve_undo,      # same recipients as original activity
}
 
 
async def resolve_recipients(payload: dict, followers: set[str]) -> set[str]:
    async def _resolve_default(payload: dict, followers: set[str]) -> set[str]:
        return followers

    resolver = _RESOLVERS.get(payload.get("type", ""), _resolve_default)
    return await resolver(payload, followers)

