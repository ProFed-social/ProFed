# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional
from profed.topics.incoming_activities_topic import REACTION_VERBS
from profed.topics.statuses_topic import inner_object_id


PREFERRED = ("emojiReactions", "likes")


def _link(value) -> Optional[str]:
    return (value
            if isinstance(value, str) and value else
            value.get("id")
            if isinstance(value, dict) and isinstance(value.get("id"), str) else
            None)


def collection_url(obj: dict) -> Optional[str]:
    return next((url for url in (_link(obj.get(name)) for name in PREFERRED) if url), None)


def total_of(collection: dict) -> Optional[int]:
    total = collection.get("totalItems")
    return total if isinstance(total, int) and total >= 0 else None


def page_of(document: dict) -> tuple:
    listed = document.get("orderedItems") or document.get("items") or []
    return ([item for item in listed if isinstance(item, dict)] if isinstance(listed, list) else [],
            _link(document.get("next")))


def start_of(collection: dict) -> tuple:
    first = collection.get("first")
    return (page_of(first)
            if isinstance(first, dict) else
            ([], _link(first))
            if first is not None else
            page_of(collection))


def is_reaction_of(item: dict, object_url: str) -> bool:
    return (item.get("type") in REACTION_VERBS and
            isinstance(item.get("id"), str) and
            isinstance(item.get("actor"), str) and
            bool(item.get("id")) and
            bool(item.get("actor")) and
            inner_object_id(item.get("object")) == object_url)


def reactions_of(items: list, object_url: str) -> list:
    return [item for item in items if isinstance(item, dict) and is_reaction_of(item, object_url)]


def enough(seen: int, pages: int, total: Optional[int], max_pages: int) -> bool:
    return pages >= max_pages or (total is not None and seen >= total)

