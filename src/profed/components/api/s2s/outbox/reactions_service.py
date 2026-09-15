# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional
from profed.identity import actor_url_from_username
from .reactions_storage import storage


PAGE_SIZE = 40

CONTEXT = "https://www.w3.org/ns/activitystreams"

COLLECTIONS = {"likes": False, "emojiReactions": True}


def note_url(username: str, note_id: str) -> str:
    return f"{actor_url_from_username(username)}/notes/{note_id}"


def collection_url(username: str, note_id: str, name: str) -> str:
    return f"{note_url(username, note_id)}/{name}"


def _like(row: dict, object_url: str) -> dict:
    return {"id": row["reaction_url"],
            "type": "Like",
            "actor": row["actor_url"],
            "object": object_url,
            **({"content": row["emoji"]} if row["emoji"] else {})}


def _next_url(url: str, rows: list) -> Optional[str]:
    return f"{url}?page=true&before={rows[-1]['status_id']}" if len(rows) == PAGE_SIZE else None


async def _page(url: str, object_url: str, emoji_only: bool, before: Optional[int]) -> dict:
    rows = await (await storage()).page(object_url, PAGE_SIZE, before, emoji_only)
    return {"@context": CONTEXT,
            "id": f"{url}?page=true" + (f"&before={before}" if before is not None else ""),
            "type": "OrderedCollectionPage",
            "partOf": url,
            "orderedItems": [_like(row, object_url) for row in rows],
            **({"next": _next_url(url, rows)} if _next_url(url, rows) else {})}


async def _collection(url: str, object_url: str, emoji_only: bool) -> dict:
    return {"@context": CONTEXT,
            "id": url,
            "type": "OrderedCollection",
            "totalItems": await (await storage()).count_for(object_url, emoji_only),
            "first": f"{url}?page=true"}


async def resolve_reactions(username: str, note_id: str, name: str, page: bool, before: Optional[int]) -> dict:
    url = collection_url(username, note_id, name)
    object_url = note_url(username, note_id)
    return (await _page(url, object_url, COLLECTIONS[name], before)
            if page or before is not None else
            await _collection(url, object_url, COLLECTIONS[name]))
